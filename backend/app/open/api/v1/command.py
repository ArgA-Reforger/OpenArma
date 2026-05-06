import json
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.conversation.model.conversation import Conversation
from backend.app.conversation.model.message import Message
from backend.app.open.crud.crud_arma_config import arma_config_dao
from backend.app.open.crud.crud_command_pool import (
    get_all_pending_orders_by_project,
    mark_delivered,
)
from backend.app.open.model.arma_config import ArmaConfig
from backend.app.open.model.battle_snapshot import BattleSnapshot
from backend.app.open.schema.command import (
    ArmaConfigBlock,
    CommandResponse,
    PendingOrders,
    SideConfigBlock,
    SituationReportRequest,
)
from backend.app.open.service.command_service import CommandService
from backend.app.open.service.fog_of_war import filter_for_faction
from backend.app.project.crud.crud_project import project_dao
from backend.common.log import log
from backend.database.db import get_db

router = APIRouter()


async def _resolve_api_key(
    x_api_key: Optional[str] = Header(None, alias='X-API-Key'),
    api_key: Optional[str] = Query(None),
) -> str:
    key = x_api_key or api_key
    if not key:
        raise HTTPException(status_code=401, detail='API Key required (header X-API-Key or query param api_key)')
    return key


def _build_config_block(config: ArmaConfig | None) -> ArmaConfigBlock:
    if config:
        sides_raw = config.sides_list
        return ArmaConfigBlock(
            running=config.running,
            decision_interval=config.decision_interval,
            sides=[SideConfigBlock(faction=s['faction'], control=s['control']) for s in sides_raw],
            max_squads=config.max_squads,
            emergency_enabled=config.emergency_enabled,
            language=config.language,
        )
    return ArmaConfigBlock()


async def _get_or_create_arma_conversation(
    db: AsyncSession,
    project_id: int,
    owner_id: int,
    side: str | None = None,
    is_llm_side: bool = False,
    group_id: int | None = None,
) -> Conversation:
    """Find active Arma conversation for this project+side (scoped by group_id), or create one.
    If is_llm_side=True and the conversation has no agent, auto-bind the first available."""
    stmt = sa_select(Conversation).where(
        Conversation.project_id == project_id,
        Conversation.source == 'arma',
        Conversation.status == 'active',
        Conversation.del_flag == False,  # noqa: E712
    )
    if group_id:
        stmt = stmt.where(Conversation.conversation_group_id == group_id)
    if side is not None:
        stmt = stmt.where(Conversation.side == side)
    else:
        stmt = stmt.where(Conversation.side.is_(None))

    stmt = stmt.order_by(Conversation.created_time.desc()).limit(1)
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()

    if not conv:
        agent_id = None
        if is_llm_side:
            agent_id = await _find_agent_for_owner(db, owner_id)
        title = f'Arma Commander - {side}' if side else 'Arma AI Commander'
        conv = Conversation(
            project_id=project_id,
            user_id=owner_id,
            title=title,
            source='arma',
            side=side,
            status='active',
            agent_id=agent_id,
            conversation_group_id=group_id,
        )
        db.add(conv)
        await db.flush()
        await db.refresh(conv)
        log.info('Created Arma conversation: id=%s, project=%s, side=%s, agent=%s, group=%s',
                 conv.id, project_id, side, agent_id, group_id)
    elif conv.agent_id is None and is_llm_side:
        agent_id = await _find_agent_for_owner(db, owner_id)
        if agent_id:
            conv.agent_id = agent_id
            await db.flush()
            log.info('Auto-bound agent %s to Arma conversation %s (side=%s)', agent_id, conv.id, side)

    return conv


async def _find_agent_for_owner(db: AsyncSession, owner_id: int) -> int | None:
    """Find the first usable agent for this user (default first, then any)."""
    from backend.app.agent.crud.crud_agent import agent_dao
    default_agent = await agent_dao.get_default(db, owner_id)
    if default_agent:
        return default_agent.id
    from backend.app.agent.model.agent import Agent
    stmt = sa_select(Agent.id).where(
        Agent.user_id == owner_id,
        Agent.del_flag == False,  # noqa: E712
    ).limit(1)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    return row


async def _get_pending_web_messages(db: AsyncSession, conversation_id: int, limit: int = 10) -> list[dict]:
    """Fetch recent web-sourced messages not yet delivered to the mod."""
    stmt = (
        sa_select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.role == 'user',
            Message.del_flag == False,  # noqa: E712
        )
        .order_by(Message.created_time.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    web_msgs = []
    for msg in reversed(messages):
        meta = msg.metadata_ or {}
        if meta.get('source') == 'web' and not meta.get('delivered_to_mod'):
            web_msgs.append({
                'id': msg.id,
                'text': msg.content or '',
                'priority': meta.get('priority', 'normal'),
                'sender': 'WebUser',
                'time': msg.created_time.strftime('%H:%M') if msg.created_time else '',
            })
            meta['delivered_to_mod'] = True
            msg.metadata_ = {**meta}
    return web_msgs


async def _save_battle_snapshot(
    db: AsyncSession,
    project_id: int,
    request: SituationReportRequest,
    situation_data: dict,
    conversation_group_id: int | None = None,
) -> BattleSnapshot:
    """Save a full battle snapshot from the heartbeat data."""
    snapshot = BattleSnapshot(
        project_id=project_id,
        conversation_group_id=conversation_group_id,
        request_id=request.request_id,
        game_time=situation_data.get('game_state', {}).get('game_time'),
        timestamp=request.timestamp,
        game_state=situation_data.get('game_state'),
        units=situation_data.get('units'),
        groups=situation_data.get('groups'),
        vehicles=situation_data.get('vehicles'),
        known_enemies=_extract_all_known_enemies(situation_data.get('groups', [])),
        events=situation_data.get('events'),
        markers=situation_data.get('markers'),
        human_messages=situation_data.get('human_messages'),
    )
    db.add(snapshot)
    await db.flush()
    return snapshot


def _extract_all_known_enemies(groups: list[dict]) -> list[dict]:
    """Flatten known_enemies from all groups into a single list with observer info."""
    result: list[dict] = []
    for g in groups:
        group_id = g.get('id', '')
        faction = g.get('faction', '')
        enemies = g.get('known_enemies', [])
        if not isinstance(enemies, list):
            continue
        for e in enemies:
            result.append({
                'observer_group_id': group_id,
                'observer_faction': faction,
                **e,
            })
    return result


@router.post('/command', response_model=CommandResponse)
async def submit_situation_report(
    raw_request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(_resolve_api_key),
):
    """
    Submit a battlefield situation report and receive pending orders + config.

    Init request (request_id=0 or groups=[]): creates/reuses Arma conversations,
    returns config + conversation_id. Skips AI processing.

    Heartbeat request: saves BattleSnapshot, dispatches AI processing per LLM faction,
    returns merged pending orders + config + web_messages.
    """
    project = await project_dao.get_by_api_key(db, api_key)
    if not project:
        raise HTTPException(status_code=401, detail='Invalid API Key')
    if project.status != 'active':
        raise HTTPException(status_code=403, detail='Project is not active')

    body = await raw_request.body()
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=400, detail=f'Invalid JSON body: {e}')

    request = SituationReportRequest(**data)
    arma_config = await arma_config_dao.get_by_project(db, project.id)
    config_block = _build_config_block(arma_config)

    is_init = request.request_id == 0 or not request.groups

    sides = arma_config.sides_list if arma_config else []
    llm_sides = [s for s in sides if s.get('control') == 'llm']

    llm_faction_set = {s['faction'] for s in llm_sides}
    cfg_group_id = arma_config.conversation_group_id if arma_config else None
    for side_cfg in sides:
        await _get_or_create_arma_conversation(
            db, project.id, project.owner_id, side=side_cfg['faction'],
            is_llm_side=side_cfg['faction'] in llm_faction_set,
            group_id=cfg_group_id,
        )

    primary_side = llm_sides[0]['faction'] if llm_sides else (sides[0]['faction'] if sides else None)
    primary_conv = await _get_or_create_arma_conversation(
        db, project.id, project.owner_id,
        side=primary_side,
        is_llm_side=primary_side in llm_faction_set if primary_side else False,
        group_id=cfg_group_id,
    )
    conversation_id = str(primary_conv.id)

    if is_init:
        await db.commit()
        return CommandResponse(
            ack=True,
            request_id=request.request_id,
            status='init',
            config=config_block,
            conversation_id=conversation_id,
        )

    situation_data = request.model_dump()

    await _save_battle_snapshot(db, project.id, request, situation_data, conversation_group_id=cfg_group_id)

    merged_orders: list[dict] = []
    merged_briefings: list[str] = []
    merged_assessments: list[str] = []
    merged_priority_targets: list[str] = []
    has_pending = False

    pool_entries = await get_all_pending_orders_by_project(db, project.id)
    for pool_entry in pool_entries:
        if pool_entry.orders_json:
            has_pending = True
            merged_orders.extend(pool_entry.orders_json.get('orders', []))
            briefing = pool_entry.orders_json.get('briefing', '')
            if briefing:
                merged_briefings.append(briefing)
            assessment = pool_entry.orders_json.get('assessment', '')
            if assessment:
                merged_assessments.append(assessment)
            merged_priority_targets.extend(pool_entry.orders_json.get('priority_targets', []))
        await mark_delivered(db, pool_entry)

    pending = None
    if has_pending:
        pending = PendingOrders(
            request_id=request.request_id,
            orders=merged_orders,
            briefing=' | '.join(merged_briefings) if merged_briefings else '',
            assessment=' | '.join(merged_assessments) if merged_assessments else '',
            priority_targets=merged_priority_targets,
        )

    all_web_messages: list[dict] = []
    for side_cfg in llm_sides:
        conv = await _get_or_create_arma_conversation(
            db, project.id, project.owner_id, side=side_cfg['faction'],
            is_llm_side=True,
            group_id=cfg_group_id,
        )
        web_msgs = await _get_pending_web_messages(db, conv.id)
        all_web_messages.extend(web_msgs)

    if config_block.running and llm_sides:
        for side_cfg in llm_sides:
            faction = side_cfg['faction']
            conv = await _get_or_create_arma_conversation(
                db, project.id, project.owner_id, side=faction,
                is_llm_side=True,
                group_id=cfg_group_id,
            )

            fog_data = filter_for_faction(situation_data, faction, sides)

            side_web_msgs = [m for m in all_web_messages if True]
            if side_web_msgs:
                existing_human = fog_data.get('human_messages', [])
                for wm in side_web_msgs:
                    existing_human.append({
                        'text': wm['text'],
                        'sender': wm['sender'],
                        'time': wm.get('time', ''),
                        'source': 'web',
                        'priority': wm.get('priority', 'normal'),
                    })
                fog_data['human_messages'] = existing_human

            await CommandService.process_situation_report(
                project_id=project.id,
                conversation_id=str(conv.id),
                request_id=request.request_id,
                situation_data=fog_data,
                priority=request.priority,
            )

    await db.commit()

    status = 'ready' if pending else ('processing' if config_block.running else 'idle')
    return CommandResponse(
        ack=True,
        request_id=request.request_id,
        status=status,
        pending_orders=pending,
        config=config_block,
        web_messages=[{'text': m['text'], 'sender': m['sender']} for m in all_web_messages],
        conversation_id=conversation_id,
    )
