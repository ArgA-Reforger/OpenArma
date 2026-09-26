"""Arma Commander situation report processing Celery task.

Phase 1.5: fully reuses ChatService's Agent orchestration capability.
Situation report = one user message -> ChatService runs the full pipeline -> Output Processor extracts orders.
"""

import json
import logging
import time

from backend.app.task.celery import celery_app

log = logging.getLogger(__name__)

SYSTEM_RULES = (
    '\n\nIMPORTANT SYSTEM RULES (engine constraints — do NOT override):\n'
    '1. Coordinate system: X axis = East(+)/West(-), Z axis = North(+)/South(-), Y axis = altitude.\n'
    # These four Chinese vocabulary words are literal terms the LLM may see in
    # incoming game chat/messages; kept as escapes so the mapping still matches
    # that raw text if it appears (behavior-preserving, not a translation).
    '   "\u53f3\u79fb" means move East (+X), "\u5de6\u79fb" means move West (-X), '
    '"\u524d\u8fdb" means move North (+Z), "\u540e\u9000" means move South (-Z).\n'
    '2. Your final response MUST be valid JSON with this structure:\n'
    '{"orders": [{"type": "move"|"force_move"|"defend"|"attack"|"patrol"|"hold"|"retreat"|"route",'
    ' "group_id": "<id>", "target": [x, y, z], ...}],'
    ' "briefing": "<short summary>",'
    ' "assessment": "<threat assessment>",'
    ' "priority_targets": ["<target description>"]}\n'
    '3. For patrol and route orders, use "waypoints" as array of objects: '
    '[{"pos": [x,y,z]}, {"pos": [x,y,z]}, ...] (NOT bare arrays).\n'
    '   - "patrol" = cyclic loop (A→B→C→A→B→C...), use for area security.\n'
    '   - "route" = one-way march (A→B→C then stop), use for tactical movement along a path.\n'
    '4. Do NOT include any text outside the JSON object. No markdown code fences, '
    'no explanatory text outside the JSON.\n'
    '5. Use the EXACT group_id from the situation report (e.g., "0x4000000000000081").\n'
    '6. ONLY generate orders for groups listed in the situation report. '
    'Do NOT invent group_ids that are not present in the report.\n'
    '7. ALWAYS include the "briefing" field in your response, even if no orders change.\n'
    '8. If the WARNING section says squads have not moved, re-issue movement orders. '
    'Do NOT assume previous orders succeeded — always verify by checking if positions changed.\n'
    '9. If a squad is stationary and you want it to move, ALWAYS issue a new order. '
    'It is better to re-issue a redundant order than to leave a squad idle.\n'
    '10. TIMING: Your orders will NOT execute immediately. There is a ~30-60 second delay '
    'between your response and order execution in-game. Plan ahead: '
    'if enemies are 200m away and closing, target positions should account for their movement '
    'during this delay. Do not assume instantaneous execution.\n'
    '11. DEFEND orders are TEMPORARY — they expire after ~120 seconds. '
    'After that, the squad becomes idle. You MUST follow up with new orders. '
    'If a squad\'s status shows "orders: defend" and you want it to MOVE, '
    'you MUST issue a "move" or "patrol" order — the defend will be replaced.\n'
    '12. FIRST REPORT: On the very first situation report, you MUST issue valid orders for ALL squads. '
    'Do not output only analysis text — always include a JSON with concrete orders.\n'
    '13. STUCK DETECTION: If a squad has been at the exact same position for 3+ consecutive reports, '
    'it means your previous order was not effective. You MUST issue a different order or '
    'a significantly different target position. Do not repeat the same defend coordinates. '
    'Try "force_move" if regular "move" keeps failing.\n'
    '14. DESTROYED GROUPS: If a group_id from your previous orders no longer appears in the '
    'current situation report, that group has been destroyed. Stop issuing orders for it. '
    'Adapt your plan to account for reduced forces.\n'
    '15. PROTECT PATROLS (CRITICAL): If a squad\'s status shows "orders: patrol" and there are NO enemy contacts '
    'near that squad, you MUST NOT issue ANY new orders to it. The patrol is running as an infinite loop '
    'in the game engine — re-issuing a patrol order CANCELS the current loop and restarts from scratch, '
    'causing the squad to stop, turn around, and lose progress. This creates dangerous gaps in coverage. '
    'Only interrupt a patrol when: (a) enemies are detected nearby, (b) the squad has taken casualties '
    'and needs to withdraw, or (c) you need to reassign it to a different sector. '
    'Squads marked ">> PATROL ACTIVE" in the report MUST be skipped entirely in your orders list.\n'
    '16. DEAD ENEMIES: If an enemy contact stays at the EXACT same position across multiple reports '
    'and no one reports taking fire from that position, the enemy is likely DEAD. '
    'Do NOT keep sending squads to attack a dead body. Focus attack orders on MOVING or newly detected enemies only.\n'
    '17. STALLED ORDERS ESCALATION: If your attack/move orders fail for 3+ consecutive turns '
    'to the SAME squad: the squad is likely in active combat and the AI engine is refusing movement. '
    'STOP re-issuing the same order. Instead, issue DEFEND at the squad\'s CURRENT position '
    'or send a DIFFERENT squad to flank from another direction.\n'
    '18. When responding to priority: urgent requests, focus ONLY on the emergency.\n'
    '19. NEVER use coordinates that are clearly outside the map bounds.'
)


def _split_groups_by_control(groups: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split groups into LLM-controlled and non-LLM (human/other)."""
    llm_groups = []
    other_groups = []
    for g in groups:
        if g.get('control', 'llm') == 'llm':
            llm_groups.append(g)
        else:
            other_groups.append(g)
    return llm_groups, other_groups


def _assign_tactical_roles(groups: list[dict]) -> None:
    """Assign tactical roles based on member_count.

    Groups are split into two tiers by the median member count:
    - Below median → 'recon' (patrol / screening)
    - At or above median → 'fireteam' (assault / defense)

    If all groups have the same size, everyone is 'fireteam'.
    """
    if not groups:
        return
    sizes = sorted(set(g.get('member_count', 0) for g in groups))
    if len(sizes) <= 1:
        for g in groups:
            g['tactical_role'] = 'fireteam'
        return
    threshold = sizes[len(sizes) // 2]
    for g in groups:
        mc = g.get('member_count', 0)
        g['tactical_role'] = 'recon' if mc < threshold else 'fireteam'


def format_situation_report(situation_data: dict, request_id: int, priority: str) -> str:
    """Format raw situation data into LLM-friendly text.

    Only LLM-controlled groups are included in the report sent to the AI.
    Non-LLM groups are stored in the situation log but not shown to the LLM.
    """
    game_state = situation_data.get('game_state', {})
    groups = situation_data.get('groups', [])
    human_messages = situation_data.get('human_messages', [])
    timestamp = situation_data.get('timestamp', 0)

    llm_groups, _other = _split_groups_by_control(groups)
    _assign_tactical_roles(llm_groups)
    prev_situation = situation_data.get('_prev_situation')

    lines: list[str] = []
    lines.append(f'=== SITUATION REPORT (Request #{request_id}, T={timestamp}) ===')
    lines.append(f'Priority: {priority}')
    lines.append('')

    if game_state:
        lines.append('== GAME STATE ==')
        for key in ('game_mode', 'game_time', 'weather', 'visibility', 'terrain'):
            val = game_state.get(key)
            if val is not None:
                lines.append(f'{key.replace("_", " ").title()}: {val}')
        lines.append('')

    if llm_groups:
        recon_count = sum(1 for g in llm_groups if g.get('tactical_role') == 'recon')
        fire_count = len(llm_groups) - recon_count
        lines.append(f'== YOUR FORCES ({len(llm_groups)} squads: {recon_count} recon, {fire_count} fireteam) ==')
        lines.append('')
        for i, g in enumerate(llm_groups, 1):
            label = g.get('label', g.get('name', 'Unknown'))
            desc = g.get('description', '')
            gid = g.get('id', '')
            faction = g.get('faction', '')
            tac_role = g.get('tactical_role', 'fireteam')
            role_tag = 'RECON' if tac_role == 'recon' else 'FIRETEAM'
            header = f'[Squad {i}: {label}] [{role_tag}]'
            if desc:
                header += f' — {desc}'
            lines.append(f'{header} (faction: {faction}, id: {gid})')
            pos = g.get('position')
            if pos:
                lines.append(f'  Position: {pos}')
            members = g.get('member_count', '?')
            casualties = g.get('casualties', 0)
            lines.append(f'  Strength: {members} members, {casualties} casualties')
            wp_type = g.get('current_waypoint_type', 'none')
            speed = g.get('speed_mode', '')
            in_veh = g.get('in_vehicle', False)
            stance = g.get('leader_stance', '')
            status_parts = [f'orders: {wp_type}']
            if speed:
                status_parts.append(f'speed: {speed}')
            if in_veh:
                status_parts.append('mounted')
            if stance:
                status_parts.append(f'stance: {stance}')
            lines.append(f'  Status: {", ".join(status_parts)}')
            combat_mode = g.get('combat_mode')
            if combat_mode:
                lines.append(f'  Combat mode: {combat_mode}')
            known_enemies = g.get('known_enemies')
            has_nearby_threat = isinstance(known_enemies, list) and len(known_enemies) > 0
            if wp_type == 'patrol' and not has_nearby_threat:
                lines.append('  >> PATROL ACTIVE, no threats — DO NOT re-issue orders to this squad')
            if isinstance(known_enemies, list) and known_enemies:
                lines.append(f'  Known enemies: {len(known_enemies)} contact(s)')
                sorted_ke = sorted(known_enemies, key=lambda e: (
                    0 if e.get('time_since_endangered', 9999) < 10 else 1,
                    e.get('distance', 99999),
                ))
                for e in sorted_ke[:5]:
                    epos = e.get('position', [])
                    age = e.get('time_since_seen', 999)
                    dist = e.get('distance', -1)
                    utype = e.get('unit_type', 'unknown')
                    faction = e.get('perceived_faction', 'unknown')
                    identified = e.get('time_since_side_recognized', 9999) < 999
                    endangering = e.get('time_since_endangered', 9999) < 10
                    tags = []
                    if identified:
                        tags.append(f'faction:{faction}')
                    if endangering:
                        tags.append('THREATENING')
                    if e.get('is_disarmed'):
                        tags.append('disarmed')
                    tag_str = f' [{", ".join(tags)}]' if tags else ''
                    dist_str = f', {dist:.0f}m away' if dist >= 0 else ''
                    lines.append(f'    - {utype} at {epos}, seen {age:.0f}s ago{dist_str}{tag_str}')
            elif isinstance(known_enemies, (int, float)):
                lines.append(f'  Known enemies: {known_enemies}')
            env = g.get('environment', {})
            if env and env.get('elevation'):
                lines.append(f'  Elevation: {env["elevation"]:.0f}m')
            lines.append('')

    if prev_situation:
        prev_groups = {g['id']: g for g in prev_situation.get('groups', []) if g.get('id')}
        stalled = []
        for g in llm_groups:
            gid = g.get('id', '')
            prev = prev_groups.get(gid)
            if not prev:
                continue
            pos = g.get('position', [])
            prev_pos = prev.get('position', [])
            if len(pos) >= 3 and len(prev_pos) >= 3:
                dx = abs(pos[0] - prev_pos[0])
                dz = abs(pos[2] - prev_pos[2])
                dist = (dx ** 2 + dz ** 2) ** 0.5
                if dist < 5.0:
                    stalled.append(g.get('label', gid))
        if stalled:
            lines.append(f'== WARNING: {len(stalled)} squad(s) have NOT moved since last report ==')
            for name in stalled:
                lines.append(f'  - {name}')
            lines.append('If you previously issued move/patrol orders to these squads and they still')
            lines.append('have not moved, the orders may have failed. Consider re-issuing orders.')
            lines.append('')

    if human_messages:
        lines.append('== HUMAN MESSAGES ==')
        for msg in human_messages:
            ts = msg.get('time', '??:??')
            sender = msg.get('sender', 'Unknown')
            text = msg.get('text', '')
            source = msg.get('source', 'game')
            prio = msg.get('priority', 'normal')
            prefix = f'[{ts}] {sender}'
            if source == 'web':
                prefix += ' (Web)'
            if prio == 'critical':
                prefix += ' [URGENT]'
            lines.append(f'{prefix}: {text}')
        lines.append('')

    return '\n'.join(lines)


async def _save_situation_as_message(db, conversation_id: int, situation_text: str, request_id: int,
                                     situation_data: dict, priority: str):
    """Save the formatted situation report as a user message with metadata."""
    from backend.app.conversation.model.message import Message

    all_groups = situation_data.get('groups', [])
    llm_groups, other_groups = _split_groups_by_control(all_groups)
    db.add(Message(
        conversation_id=conversation_id,
        role='user',
        content=situation_text,
        metadata_={
            'source': 'arma_mod',
            'type': 'situation_report',
            'request_id': request_id,
            'priority': priority,
            'group_count': len(all_groups),
            'llm_group_count': len(llm_groups),
            'human_group_count': len(other_groups),
            'has_human_messages': bool(situation_data.get('human_messages')),
        },
    ))
    await db.flush()


async def _save_ai_response(db, conversation_id: int, response_text: str, orders_json: dict):
    """Save AI response as assistant message with orders metadata."""
    from backend.app.conversation.model.message import Message

    db.add(Message(
        conversation_id=conversation_id,
        role='assistant',
        content=response_text,
        structured_data=orders_json if orders_json.get('orders') else None,
        metadata_={
            'source': 'ai',
            'type': 'tactical_response',
            'has_orders': bool(orders_json.get('orders')),
            'order_count': len(orders_json.get('orders', [])),
        },
    ))
    await db.flush()


async def _build_battlefield_memory(
    db, conversation_id: str, current_request_id: int,
    mission_objective: dict | None, map_id: int | None,
    project_id: int | None = None,
) -> str:
    """Build battlefield memory context from recent battle snapshots and config."""
    from backend.app.open.model.battle_snapshot import BattleSnapshot
    from sqlalchemy import select

    sections: list[str] = []

    if mission_objective and mission_objective.get('type') != 'none':
        sections.append('== MISSION OBJECTIVE (HIGHEST PRIORITY) ==')
        sections.append(f"Type: {mission_objective.get('type', 'unknown')}")
        sections.append(f"Description: {mission_objective.get('description', 'N/A')}")
        targets = mission_objective.get('primary_targets', [])
        if targets:
            for t in targets:
                sections.append(f"  Target: {t.get('name', '?')} at {t.get('position', '?')} ({t.get('type', '?')})")
        constraints = mission_objective.get('constraints')
        if constraints:
            sections.append(f"Constraints: {constraints}")

        ao = mission_objective.get('ao')
        if ao:
            fps = ao.get('focus_points', [])
            if fps:
                sections.append('KEY POSITIONS (you MUST orient operations around these):')
                for fp in fps:
                    pos = fp.get('position', [])
                    label = fp.get('label', 'Unnamed')
                    radius = fp.get('radius', 1000)
                    if len(pos) >= 2:
                        sections.append(
                            f'  * {label} at coordinates [{pos[0]}, {pos[1]}], '
                            f'operational radius {radius}m'
                        )
                    else:
                        sections.append(f'  * {label}, radius {radius}m')
                sections.append(
                    'ALL deployment, patrol, and defense orders MUST be within or '
                    'oriented toward these key positions. Do NOT ignore them.'
                )
        sections.append('')

    ao_config = mission_objective.get('ao') if mission_objective else None
    if ao_config and project_id:
        from backend.app.map.service.ao_briefing import get_cached_briefing
        briefing = await get_cached_briefing(project_id)
        if briefing:
            sections.append(briefing)
            sections.append('')

    if map_id:
        sections.append(f'== MAP CONTEXT == (map_id: {map_id})')
        sections.append('Use query_landmarks, get_area_intel, query_terrain_cells, and other map tools to look up locations.')
        sections.append('Use query_terrain_cells with natural language to find specific terrain features.')
        sections.append('Reference landmarks by name in briefings for clarity.')
        sections.append('')

    if project_id:
        snap_stmt = (
            select(BattleSnapshot)
            .where(BattleSnapshot.project_id == project_id)
            .where(BattleSnapshot.request_id < current_request_id)
            .order_by(BattleSnapshot.request_id.desc())
            .limit(10)
        )
        snap_result = await db.execute(snap_stmt)
        recent_snapshots = list(snap_result.scalars().all())
        recent_snapshots.reverse()
    else:
        recent_snapshots = []

    if recent_snapshots:
        all_enemy_positions: list[dict] = []
        total_casualties = 0

        for snap in recent_snapshots:
            groups = snap.groups or []
            llm_only, _ = _split_groups_by_control(groups)
            for g in llm_only:
                for e in g.get('known_enemies', []):
                    pos = e.get('position')
                    if pos:
                        all_enemy_positions.append({
                            'position': pos,
                            'request_id': snap.request_id,
                        })
                total_casualties += g.get('casualties', 0)

            known = snap.known_enemies or []
            for ke in known:
                pos = ke.get('position')
                if pos:
                    all_enemy_positions.append({
                        'position': pos,
                        'request_id': snap.request_id,
                    })

        if all_enemy_positions:
            sections.append(f'== ENEMY CONTACT HISTORY (last {len(recent_snapshots)} cycles) ==')
            unique_areas: dict[str, int] = {}
            for ep in all_enemy_positions:
                pos = ep['position']
                grid_key = f"{int(pos[0] / 200) * 200},{int(pos[2] / 200) * 200}" if len(pos) >= 3 else str(pos)
                unique_areas[grid_key] = unique_areas.get(grid_key, 0) + 1
            for area, count in sorted(unique_areas.items(), key=lambda x: -x[1])[:5]:
                sections.append(f"  Hot zone near [{area}]: {count} contact(s)")
            sections.append('')

        if total_casualties > 0:
            sections.append(f'== CUMULATIVE CASUALTIES: {total_casualties} ==')
            sections.append('')

    from backend.app.open.model.command_pool import CommandPool
    from sqlalchemy import select as sa_select
    cmd_stmt = (
        sa_select(CommandPool)
        .where(CommandPool.conversation_id == conversation_id)
        .order_by(CommandPool.created_time.desc())
        .limit(3)
    )
    cmd_result = await db.execute(cmd_stmt)
    recent_cmds = list(cmd_result.scalars().all())
    if recent_cmds:
        sections.append('== ORDER DELIVERY STATUS ==')
        for cmd in reversed(recent_cmds):
            orders_data = cmd.orders_json or {}
            order_count = len(orders_data.get('orders', []))
            sections.append(f"  Request #{cmd.request_id}: {order_count} orders, status={cmd.status}")
        sections.append('')

    return '\n'.join(sections) if sections else ''


MAX_ENEMIES_PER_GROUP = 5
MAX_GLOBAL_ENEMIES = 30


def _truncate_situation_for_llm(groups: list[dict]) -> list[dict]:
    """Truncate known_enemies in groups to avoid LLM token overflow.

    Keeps the closest/most threatening enemies per group and deduplicates
    across all groups to reduce redundant data.
    """
    seen_positions: set[str] = set()
    result = []
    for g in groups:
        g_copy = dict(g)
        enemies = g_copy.get('known_enemies')
        if isinstance(enemies, list) and len(enemies) > MAX_ENEMIES_PER_GROUP:
            sorted_enemies = sorted(enemies, key=lambda e: (
                0 if e.get('time_since_endangered', 9999) < 10 else 1,
                e.get('distance', 99999),
            ))
            g_copy['known_enemies'] = sorted_enemies[:MAX_ENEMIES_PER_GROUP]
        result.append(g_copy)

    global_enemies = []
    for g in result:
        for e in g.get('known_enemies', []):
            pos = e.get('position', [])
            if len(pos) >= 3:
                key = f"{int(pos[0])},{int(pos[2])}"
                if key not in seen_positions:
                    seen_positions.add(key)
                    global_enemies.append(e)

    if len(global_enemies) > MAX_GLOBAL_ENEMIES:
        global_enemies.sort(key=lambda e: e.get('distance', 99999))
        drop_positions = {
            f"{int(e.get('position', [0,0,0])[0])},{int(e.get('position', [0,0,0])[2])}"
            for e in global_enemies[MAX_GLOBAL_ENEMIES:]
            if len(e.get('position', [])) >= 3
        }
        for g in result:
            enemies = g.get('known_enemies')
            if isinstance(enemies, list):
                g['known_enemies'] = [
                    e for e in enemies
                    if len(e.get('position', [])) < 3
                    or f"{int(e['position'][0])},{int(e['position'][2])}" not in drop_positions
                ]

    return result


@celery_app.task(name='process_situation', bind=True, max_retries=2)
async def process_situation_task(
    self,
    *,
    project_id: int,
    conversation_id: str,
    request_id: int,
    situation_data: dict,
    priority: str = 'normal',
) -> str:
    from backend.app.conversation.engine.graph import (
        AgentConfig,
        ConversationState,
        build_single_agent_graph,
    )
    from backend.app.conversation.service.chat_service import ChatService
    from backend.app.open.crud.crud_arma_config import arma_config_dao
    from backend.app.open.crud.crud_command_pool import create_command
    from backend.app.open.model.situation_log import SituationLog
    from backend.app.open.service.arma_output_processor import extract_orders_from_response
    from sqlalchemy import select
    from backend.app.open.service.message_queue import acquire_lock, release_lock
    from backend.app.project.crud.crud_project import project_dao
    from backend.database.db import async_db_session

    t0 = time.monotonic()

    try:
        from backend.utils.snowflake import snowflake
        if not snowflake._initialized:
            await snowflake.init()

        locked = await acquire_lock(conversation_id)
        if not locked:
            log.info('Conv %s is locked, re-queuing request #%s', conversation_id, request_id)
            from backend.app.open.service.message_queue import enqueue_situation
            await enqueue_situation(conversation_id, request_id, situation_data, priority)
            return f'Request {request_id} re-queued (locked)'

        try:
            async with async_db_session() as db:
                project = await project_dao.get(db, project_id)
                if not project:
                    raise ValueError(f'Project {project_id} not found')

                conv_id_int = int(conversation_id)
                arma_config = await arma_config_dao.get_by_conversation_group(db, conv_id_int)
                if not arma_config:
                    arma_config = await arma_config_dao.get_by_project(db, project_id)
                context_window = arma_config.context_window if arma_config else 15
                project, agent_configs, _topology, _settings = (
                    await ChatService._get_agents_with_providers(
                        db, project_id, project.owner_id,
                        conversation_id=conv_id_int,
                    )
                )

                from backend.app.open.model.battle_snapshot import BattleSnapshot
                prev_stmt = (
                    select(BattleSnapshot)
                    .where(BattleSnapshot.project_id == project_id)
                    .where(BattleSnapshot.request_id < request_id)
                    .order_by(BattleSnapshot.request_id.desc())
                    .limit(1)
                )
                prev_result = await db.execute(prev_stmt)
                prev_snapshot = prev_result.scalar_one_or_none()
                if prev_snapshot and prev_snapshot.groups:
                    situation_data['_prev_situation'] = {'groups': prev_snapshot.groups}

                user_input = format_situation_report(situation_data, request_id, priority)
                situation_data.pop('_prev_situation', None)

                filtered_data = dict(situation_data)
                llm_only, _ = _split_groups_by_control(filtered_data.get('groups', []))
                filtered_data['groups'] = _truncate_situation_for_llm(llm_only)
                user_input += f'\n\n<raw_situation_json>\n{json.dumps(filtered_data)}\n</raw_situation_json>'

                await _save_situation_as_message(db, conv_id_int, user_input, request_id, situation_data, priority)

                from backend.app.conversation.service.context_manager import build_history
                llm_cfg = {
                    'provider_type': agent_configs[0]['provider_type'],
                    'api_base': agent_configs[0].get('api_base'),
                    'api_key_encrypted': agent_configs[0].get('api_key_encrypted'),
                    'model_name': agent_configs[0]['model_name'],
                }
                history = await build_history(
                    db, conv_id_int,
                    context_window=context_window,
                    llm_config=llm_cfg,
                    is_arma=True,
                )

                mission_obj = getattr(arma_config, 'mission_objective', None) if arma_config else None
                if not mission_obj:
                    from backend.app.conversation.model import Conversation
                    conv_mo_stmt = (
                        select(Conversation.mission_objective)
                        .where(Conversation.id == conv_id_int)
                        .where(Conversation.del_flag == False)  # noqa: E712
                    )
                    conv_mo_result = await db.execute(conv_mo_stmt)
                    mission_obj = conv_mo_result.scalar_one_or_none()
                map_id_val = project.map_id if project and getattr(project, 'map_id', None) else None

                battlefield_memory = await _build_battlefield_memory(
                    db, conversation_id, request_id, mission_obj, map_id_val,
                    project_id=project_id,
                )

                cfg = AgentConfig(**agent_configs[0])
                augmented_system_prompt = (cfg.system_prompt or '') + SYSTEM_RULES
                if battlefield_memory:
                    augmented_system_prompt += '\n\n' + battlefield_memory

                initial_state = ConversationState(
                    system_prompt=augmented_system_prompt,
                    rules=cfg.rules,
                    provider_type=cfg.provider_type,
                    api_base=cfg.api_base,
                    api_key_encrypted=cfg.api_key_encrypted,
                    model_name=cfg.model_name,
                    temperature=cfg.temperature,
                    top_p=cfg.top_p,
                    max_tokens=cfg.max_tokens,
                    presence_penalty=cfg.presence_penalty,
                    frequency_penalty=cfg.frequency_penalty,
                    llm_provider_id=cfg.llm_provider_id,
                    rpm_limit=cfg.rpm_limit,
                    tpm_limit=cfg.tpm_limit,
                    history=history,
                    user_input=user_input,
                    tools=cfg.tools,
                    tool_configs=cfg.tool_configs,
                    builtin_tool_handlers=cfg.builtin_tool_handlers,
                )

                graph = build_single_agent_graph()

                response_text = ''
                tool_call_log = []
                usage_data: dict = {}
                for _attempt in range(2):
                    result_state = await graph.ainvoke(initial_state)
                    response_text = result_state['response']
                    usage_data = result_state.get('usage', {})
                    tool_call_log = result_state.get('_tool_call_log') or getattr(initial_state, '_tool_call_log', [])
                    if response_text and response_text.strip():
                        break
                    log.warning(
                        'Empty LLM response for conv=%s request=%s (attempt %s), retrying...',
                        conversation_id, request_id, _attempt + 1,
                    )

                processing_time_ms = int((time.monotonic() - t0) * 1000)

                orders_json = extract_orders_from_response(response_text)
                if tool_call_log:
                    orders_json['tool_calls'] = tool_call_log

                llm_group_ids = {
                    g['id'] for g in situation_data.get('groups', [])
                    if g.get('control', 'llm') == 'llm' and g.get('id')
                }
                raw_count = len(orders_json.get('orders', []))
                orders_json['orders'] = [
                    o for o in orders_json.get('orders', [])
                    if o.get('group_id') in llm_group_ids
                ]
                filtered = raw_count - len(orders_json['orders'])
                if filtered > 0:
                    log.info(
                        'Filtered %s non-LLM orders (kept %s) for conv=%s',
                        filtered, len(orders_json['orders']), conversation_id,
                    )

                await create_command(
                    db,
                    conversation_id=conversation_id,
                    request_id=request_id,
                    orders_json=orders_json,
                    project_id=project_id,
                )

                await _save_ai_response(db, conv_id_int, response_text, orders_json)

                from backend.app.open.model.battle_snapshot import BattleSnapshot
                snap_stmt = (
                    select(BattleSnapshot)
                    .where(BattleSnapshot.project_id == project_id)
                    .where(BattleSnapshot.request_id == request_id)
                    .order_by(BattleSnapshot.created_time.desc())
                    .limit(1)
                )
                snap_result = await db.execute(snap_stmt)
                snap = snap_result.scalar_one_or_none()
                if snap:
                    snap.response_json = orders_json
                    snap.processing_time_ms = processing_time_ms

                await db.commit()

            if usage_data.get('prompt_tokens') or usage_data.get('completion_tokens'):
                await ChatService._persist_usage_records(
                    user_id=project.owner_id,
                    project_id=project_id,
                    conversation_id=conv_id_int,
                    agent_configs=agent_configs,
                    usage_records=[{
                        'provider_type': agent_configs[0]['provider_type'],
                        'model_name': agent_configs[0]['model_name'],
                        'duration_ms': processing_time_ms,
                        **usage_data,
                    }],
                    call_type='chat',
                )

            log.info(
                'Situation processed: conversation=%s, request=%s, time=%sms, orders=%s',
                conversation_id, request_id, processing_time_ms, len(orders_json.get('orders', [])),
            )
            return f'Request {request_id} processed in {processing_time_ms}ms'

        finally:
            await release_lock(conversation_id)

            from backend.app.open.service.message_queue import dequeue_all, merge_situations
            queued = await dequeue_all(conversation_id)
            if queued:
                merged = await merge_situations(queued)
                if merged:
                    log.info(
                        'Draining queue: conv=%s, merged %s items -> request #%s',
                        conversation_id, merged['merged_count'], merged['request_id'],
                    )
                    process_situation_task.delay(
                        project_id=project_id,
                        conversation_id=conversation_id,
                        request_id=merged['request_id'],
                        situation_data=merged['situation_data'],
                        priority=merged['priority'],
                    )

    except Exception as exc:
        import traceback
        log.error(
            'Situation processing failed: conversation=%s, request=%s, error=%s\n%s',
            conversation_id, request_id, exc, traceback.format_exc(),
        )
        try:
            raise self.retry(exc=exc, countdown=15)
        except self.MaxRetriesExceededError:
            log.error(
                'Situation processing permanently failed after retries: conv=%s, req=%s',
                conversation_id, request_id,
            )
            return f'Request {request_id} failed permanently: {exc}'
