"""Conversation message processing service: executes through the LangGraph engine,
supporting single/multi-Agent collaboration + RAG + MCP + builtin tools."""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent.crud.crud_agent import agent_dao
from backend.app.conversation.crud.crud_conversation import conversation_dao
from backend.app.conversation.crud.crud_conversation_resource import conversation_resource_dao
from backend.app.conversation.crud.crud_message import message_dao
from backend.app.conversation.engine.builtin_tools import builtin_registry
from backend.app.conversation.engine.graph import (
    AgentConfig,
    ConversationState,
    run_graph_streaming,
)
from backend.app.llm.crud.crud_llm_provider import llm_provider_dao
from backend.app.project.crud.crud_project import project_dao
from backend.common.exception import errors

log = logging.getLogger(__name__)

TITLE_SYSTEM_PROMPT = (
    'Based on the following conversation content, generate a short conversation title '
    '(no more than 6 words), written in the same language as the conversation. '
    'Return only the title text, with no quotes, punctuation, or explanation.'
)


class ChatService:

    @staticmethod
    async def _build_agent_config(
        db: AsyncSession, agent: Any, project_id: int
    ) -> dict | None:
        """Build a single agent config dict from an Agent model instance."""
        if not agent or not agent.llm_provider_id:
            return None

        provider = await llm_provider_dao.get(db, agent.llm_provider_id)
        if not provider:
            return None

        tools, tool_configs = await ChatService._get_agent_tools(db, agent.id)

        builtin_tools_list, builtin_handlers = ChatService._get_builtin_tools_for_agent(
            agent.builtin_tools,
            project_id=project_id,
            db=db,
        )
        tools = builtin_tools_list + tools

        rules_list = agent.rules if isinstance(agent.rules, list) else []

        return {
            'agent_id': agent.id,
            'agent_name': agent.name,
            'system_prompt': agent.system_prompt or '',
            'rules': rules_list,
            'provider_type': provider.provider_type,
            'api_base': provider.api_base,
            'api_key_encrypted': provider.api_key_encrypted,
            'model_name': agent.model_name or 'gpt-4',
            'temperature': agent.temperature,
            'top_p': agent.top_p,
            'max_tokens': agent.max_tokens,
            'presence_penalty': agent.presence_penalty,
            'frequency_penalty': agent.frequency_penalty,
            'tools': tools,
            'tool_configs': tool_configs,
            'llm_provider_id': provider.id,
            'rpm_limit': provider.rpm_limit,
            'tpm_limit': provider.tpm_limit,
            'builtin_tool_handlers': builtin_handlers,
            'enable_sub_agents': bool(agent.enable_sub_agents),
        }

    @staticmethod
    async def _get_agents_with_providers(
        db: AsyncSession, project_id: int, user_id: int, conversation_id: int | None = None,
    ) -> tuple[Any, list[dict], Any, dict | None]:
        """
        Load the Agent / Topology and its LLM Provider and tool config from the conversation-level binding.
        Priority: conversation.topology_id > conversation.agent_id > the user's default Agent.

        :return: (project, agent_configs_list, topology_json, project_settings)
        """
        project = await project_dao.get(db, project_id)
        if not project or project.owner_id != user_id:
            raise errors.NotFoundError(msg='Project does not exist')

        topology = None
        agent_configs: list[dict] = []

        conversation = await conversation_dao.get(db, conversation_id) if conversation_id else None

        if conversation and conversation.topology_id:
            from backend.app.topology.crud.crud_topology import topology_dao
            topo = await topology_dao.get(db, conversation.topology_id)
            if topo and topo.topology_json:
                topology = topo.topology_json
                agent_ids_in_topo: set[int] = set()
                for node in topology.get('nodes', []):
                    ndata = node.get('data', {})
                    aid = ndata.get('agentId') or ndata.get('agent_id')
                    if aid:
                        agent_ids_in_topo.add(int(aid))
                for aid in agent_ids_in_topo:
                    agent = await agent_dao.get(db, aid)
                    cfg = await ChatService._build_agent_config(db, agent, project_id)
                    if cfg:
                        agent_configs.append(cfg)

        elif conversation and conversation.agent_id:
            agent = await agent_dao.get(db, conversation.agent_id)
            cfg = await ChatService._build_agent_config(db, agent, project_id)
            if cfg:
                agent_configs.append(cfg)

        if not agent_configs:
            default_agent = await agent_dao.get_default(db, user_id)
            if default_agent:
                cfg = await ChatService._build_agent_config(db, default_agent, project_id)
                if cfg:
                    agent_configs.append(cfg)

        if not agent_configs:
            raise errors.RequestError(msg='No valid Agent configured (an Agent + LLM provider is required)')

        settings = project.settings or {}

        map_context = await ChatService._build_map_context(db, project_id)
        if map_context:
            for cfg in agent_configs:
                has_map_tool = any(
                    t.get('name', '') in (
                        'query_landmarks', 'calculate_route', 'get_terrain_profile',
                        'get_area_intel', 'assess_threat_level', 'view_map_image',
                        'plan_route', 'get_terrain_summary', 'estimate_travel_time',
                        'convert_coordinates',
                    )
                    for t in cfg.get('tools', [])
                )
                if has_map_tool:
                    cfg['system_prompt'] = (cfg.get('system_prompt') or '') + map_context

        return project, agent_configs, topology, settings

    @staticmethod
    async def _build_map_context(db: AsyncSession, project_id: int) -> str:
        """Build map context string for agents with map tools enabled."""
        try:
            map_id: int | None = None

            project = await project_dao.get(db, project_id)
            if project and project.map_id:
                map_id = project.map_id

            if not map_id:
                return ''

            from backend.app.map.crud.crud_map import map_dao
            game_map = await map_dao.get(db, map_id)
            if not game_map:
                return ''

            grid_max_x = int(game_map.size_x / 100)
            grid_max_z = int(game_map.size_z / 100)
            ctx = (
                f'\n\n== MAP CONTEXT ==\n'
                f'map_id: {map_id}\n'
                f'map_name: {game_map.name}\n'
                f'map_size: {game_map.size_x}m x {game_map.size_z}m\n'
                f'Always pass map_id={map_id} when calling map tools.\n'
                f'\n'
                f'== COORDINATE SYSTEMS ==\n'
                f'1. World coordinates [x, z]: used by all map tools. Range: x=[0,{game_map.size_x}], z=[0,{game_map.size_z}]\n'
                f'2. 6-digit grid reference (XXXYYY): used when communicating with human commanders.\n'
                f'   - XXX = easting (0-{grid_max_x:03d}), YYY = northing (0-{grid_max_z:03d})\n'
                f'   - Conversion: world_x = XXX * 100, world_z = YYY * 100\n'
                f'   - Example: grid 064064 = world [6400, 6400] (map center)\n'
                f'When briefing humans, always include the 6-digit grid reference alongside world coordinates.\n'
                f'When calling tools, always use world coordinates [x, z].\n'
            )
            return ctx
        except Exception:
            log.warning('Failed to build map context', exc_info=True)
            return ''

    @staticmethod
    async def _get_history_messages(
        db: AsyncSession,
        conversation_id: int,
        limit: int = 20,
        llm_config: dict | None = None,
    ) -> list[dict]:
        from backend.app.conversation.service.context_manager import build_history

        return await build_history(
            db, conversation_id,
            context_window=limit,
            llm_config=llm_config,
        )

    @staticmethod
    async def _get_conversation_kb_ids(db: AsyncSession, conversation_id: int) -> list[int]:
        """Get the list of knowledge base IDs bound to the conversation."""
        try:
            bindings = await conversation_resource_dao.get_by_conversation(db, conversation_id, 'knowledge_base')
            return [b.resource_id for b in bindings]
        except Exception:
            log.exception('Failed to get conversation KB IDs')
            return []

    @staticmethod
    async def _get_rag_context(db: AsyncSession, conversation_id: int, query: str) -> str:
        try:
            from backend.app.knowledge.service.rag_service import build_rag_context, retrieve_context

            kb_ids = await ChatService._get_conversation_kb_ids(db, conversation_id)
            if not kb_ids:
                return ''

            results = await retrieve_context(query, kb_ids)
            return build_rag_context(results)
        except Exception:
            log.exception('RAG retrieval failed, continuing without knowledge context')
            return ''

    @staticmethod
    async def _get_agent_tools(
        db: AsyncSession, agent_id: int
    ) -> tuple[list[dict], dict[str, Any]]:
        try:
            from backend.app.mcp.crud.crud_agent_tool import agent_tool_dao
            from backend.app.mcp.crud.crud_mcp_server import mcp_server_dao
            from backend.app.mcp.crud.crud_mcp_tool import mcp_tool_dao

            bindings = await agent_tool_dao.get_by_agent(db, agent_id)
            if not bindings:
                return [], {}

            tools: list[dict] = []
            tool_configs: dict[str, Any] = {}

            for binding in bindings:
                if not binding.is_enabled:
                    continue
                mcp_tool = await mcp_tool_dao.get(db, binding.mcp_tool_id)
                if not mcp_tool:
                    continue
                server = await mcp_server_dao.get(db, mcp_tool.mcp_server_id)
                if not server or not server.is_active:
                    continue

                tools.append({
                    'name': mcp_tool.name,
                    'description': mcp_tool.description or '',
                    'input_schema': mcp_tool.input_schema or {},
                })
                tool_configs[mcp_tool.name] = {
                    'transport_type': server.transport_type,
                    'connection_config': server.connection_config,
                }

            return tools, tool_configs
        except Exception:
            log.exception('Failed to load agent tools')
            return [], {}

    @staticmethod
    def _get_builtin_tools_for_agent(
        builtin_tools_config: dict | None,
        *,
        project_id: int,
        db: AsyncSession,
    ) -> tuple[list[dict], dict]:
        """
        Build the builtin tools list and handler mapping from the Agent's builtin_tools config.

        :return: (tools_list, handlers_dict)
        """
        if not builtin_tools_config:
            return [], {}

        context = {'project_id': project_id, 'db': db}

        try:
            return builtin_registry.build_tools_for_agent(
                builtin_tools_config, context=context,
            )
        except Exception:
            log.exception('Failed to load builtin tools')
            return [], {}

    @staticmethod
    def _has_rag_tool_enabled(agent_configs: list[dict]) -> bool:
        """Check whether any Agent has the rag_retrieval builtin tool enabled."""
        for cfg in agent_configs:
            handlers = cfg.get('builtin_tool_handlers', {})
            if 'rag_retrieval' in handlers:
                return True
        return False

    @staticmethod
    async def send_message_stream(
        *,
        project_id: int,
        conversation_id: int,
        user_id: int,
        content: str,
        resend: bool = False,
    ) -> AsyncGenerator[str, None]:
        """
        Send a message and stream back the AI reply.
        When resend=True, no user message is created; used for edit-and-resend and regeneration scenarios.
        """
        from backend.app.conversation.model.message import Message
        from backend.database.db import async_db_session

        async with async_db_session() as db:
            project, agent_configs, topology, settings = await ChatService._get_agents_with_providers(
                db, project_id, user_id, conversation_id=conversation_id,
            )

            conversation = await conversation_dao.get(db, conversation_id)
            if not conversation or conversation.project_id != project_id:
                raise errors.NotFoundError(msg='Conversation does not exist')

            if resend:
                await message_dao.soft_delete_last_assistant_replies(db, conversation_id)
                await db.commit()
            else:
                user_msg = Message(
                    conversation_id=conversation_id,
                    role='user',
                    content=content,
                )
                db.add(user_msg)
                await db.commit()

            llm_cfg = {
                'provider_type': agent_configs[0]['provider_type'],
                'api_base': agent_configs[0].get('api_base'),
                'api_key_encrypted': agent_configs[0].get('api_key_encrypted'),
                'model_name': agent_configs[0]['model_name'],
            }
            history = await ChatService._get_history_messages(
                db, conversation_id, llm_config=llm_cfg,
            )

            rag_as_tool = ChatService._has_rag_tool_enabled(agent_configs)
            rag_context = ''
            if not rag_as_tool:
                rag_context = await ChatService._get_rag_context(db, conversation_id, content)

            if rag_as_tool:
                kb_ids = await ChatService._get_conversation_kb_ids(db, conversation_id)
                for cfg_dict in agent_configs:
                    handlers = cfg_dict.get('builtin_tool_handlers', {})
                    rag_handler = handlers.get('rag_retrieval')
                    if rag_handler:
                        original = rag_handler

                        async def _bound_rag(_orig=original, _kb=kb_ids, **kw: Any) -> str:
                            kw['_context'] = {'kb_ids': _kb}
                            return await _orig(**kw)

                        cfg_dict['builtin_tool_handlers']['rag_retrieval'] = _bound_rag

        use_dag = topology is not None and topology.get('nodes')
        is_multi = use_dag

        dag_compiled = None
        if use_dag:
            from backend.app.conversation.engine.graph_builder import build_dag_graph

            max_coord_rounds = settings.get('max_coordination_rounds', 1)
            initial_state = ConversationState(
                history=history,
                user_input=content,
                rag_context=rag_context,
                agent_configs=agent_configs,
                collaboration_mode='dag',
                topology=topology,
                max_coordination_rounds=max_coord_rounds,
            )
            dag_compiled = build_dag_graph(topology, agent_configs, initial_state)
        else:
            cfg = AgentConfig(**agent_configs[0])
            initial_state = ConversationState(
                system_prompt=cfg.system_prompt,
                rules=cfg.rules,
                rag_context=rag_context,
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
                user_input=content,
                tools=cfg.tools,
                tool_configs=cfg.tool_configs,
                builtin_tool_handlers=cfg.builtin_tool_handlers,
                enable_sub_agents=cfg.enable_sub_agents,
            )

        agent_message_buffers: dict[int, list[str]] = {}
        final_response: list[str] = []
        current_agent_id: int | None = None
        final_role = 'assistant'
        parent_user_msg_id: int | None = None
        usage_records: list[dict] = []

        async with async_db_session() as db:
            last_user = await message_dao.get_last_user_message(db, conversation_id)
            if last_user:
                parent_user_msg_id = last_user.id

        try:
            async for event in run_graph_streaming(initial_state, multi_agent=is_multi, dag_graph=dag_compiled):
                event_type = event.get('type', '')

                if event_type == 'token':
                    token_content = event.get('content', '')
                    agent_id = event.get('agent_id')

                    if is_multi:
                        if agent_id is not None:
                            agent_message_buffers.setdefault(agent_id, []).append(token_content)
                        else:
                            final_response.append(token_content)
                        yield json.dumps(event, ensure_ascii=False)
                    else:
                        final_response.append(token_content)
                        yield token_content

                elif event_type == 'usage':
                    usage_records.append(event)

                elif event_type in ('agent_start', 'agent_end', 'coordinator_start',
                                    'coordinator_end', 'aggregator_start', 'aggregator_end',
                                    'tool_call', 'tool_result',
                                    'node_start', 'node_end',
                                    'sub_agent_start', 'sub_agent_end',
                                    'coordinator_followup'):
                    if event_type == 'agent_start':
                        current_agent_id = event.get('agent_id')
                    elif event_type in ('coordinator_start', 'aggregator_start'):
                        final_role = event_type.replace('_start', '')
                    elif event_type == 'node_start' and event.get('agent_id'):
                        current_agent_id = event.get('agent_id')

                    if is_multi:
                        yield json.dumps(event, ensure_ascii=False)

                elif event_type == 'error':
                    yield json.dumps(event, ensure_ascii=False)
        finally:
            conv_source = getattr(conversation, 'source', None) if conversation else None
            await ChatService._persist_assistant_messages(
                conversation_id=conversation_id,
                is_multi=is_multi,
                agent_configs=agent_configs,
                agent_message_buffers=agent_message_buffers,
                final_response=final_response,
                final_role=final_role,
                parent_message_id=parent_user_msg_id,
                conversation_source=conv_source,
            )
            await ChatService._persist_usage_records(
                user_id=user_id,
                project_id=project_id,
                conversation_id=conversation_id,
                agent_configs=agent_configs,
                usage_records=usage_records,
                call_type='chat',
            )

    @staticmethod
    async def _persist_assistant_messages(
        *,
        conversation_id: int,
        is_multi: bool,
        agent_configs: list[dict],
        agent_message_buffers: dict[int, list[str]],
        final_response: list[str],
        final_role: str,
        parent_message_id: int | None = None,
        conversation_source: str | None = None,
    ) -> None:
        """Persist the assistant message. Called in a finally block to ensure it is saved even on interruption."""
        from backend.app.conversation.model.message import Message
        from backend.database.db import async_db_session

        content_to_save = ''.join(final_response)
        has_agent_content = any(bool(buf) for buf in agent_message_buffers.values())

        if not content_to_save and not has_agent_content:
            return

        try:
            async with async_db_session() as db:
                if is_multi:
                    for cfg_dict in agent_configs:
                        aid = cfg_dict['agent_id']
                        aname = cfg_dict['agent_name']
                        buffer = agent_message_buffers.get(aid, [])
                        if buffer:
                            db.add(Message(
                                conversation_id=conversation_id,
                                role='assistant',
                                content=''.join(buffer),
                                parent_message_id=parent_message_id,
                                metadata_={
                                    'agent_id': aid,
                                    'agent_name': aname,
                                    'role': 'agent',
                                },
                            ))

                    if content_to_save:
                        db.add(Message(
                            conversation_id=conversation_id,
                            role='assistant',
                            content=content_to_save,
                            parent_message_id=parent_message_id,
                            metadata_={
                                'role': final_role,
                                'is_final': True,
                            },
                        ))
                else:
                    if content_to_save:
                        structured, meta = ChatService._try_extract_arma_response(
                            content_to_save, conversation_source,
                        )
                        db.add(Message(
                            conversation_id=conversation_id,
                            role='assistant',
                            content=content_to_save,
                            structured_data=structured,
                            parent_message_id=parent_message_id,
                            metadata_=meta,
                        ))

                await db.commit()
        except Exception:
            log.exception('Failed to persist assistant messages')

    @staticmethod
    def _try_extract_arma_response(
        content: str, conversation_source: str | None,
    ) -> tuple[dict | None, dict | None]:
        """Try to parse Arma tactical JSON from assistant response.

        Returns (structured_data, metadata) or (None, None) for non-Arma conversations.
        """
        if conversation_source != 'arma':
            return None, None

        from backend.app.open.service.arma_output_processor import extract_orders_from_response

        parsed = extract_orders_from_response(content)
        has_orders = bool(parsed.get('orders'))
        has_briefing = bool(parsed.get('briefing'))

        if not has_orders and not has_briefing:
            return None, None

        structured = {
            'orders': parsed.get('orders', []),
            'briefing': parsed.get('briefing', ''),
            'assessment': parsed.get('assessment', ''),
            'priority_targets': parsed.get('priority_targets', []),
        }
        meta = {
            'source': 'ai',
            'type': 'tactical_response',
            'has_orders': has_orders,
            'order_count': len(parsed.get('orders', [])),
        }
        return structured, meta

    @staticmethod
    async def _persist_usage_records(
        *,
        user_id: int,
        project_id: int,
        conversation_id: int,
        agent_configs: list[dict],
        usage_records: list[dict],
        call_type: str = 'chat',
    ) -> None:
        """Persist usage records."""
        if not usage_records:
            return

        try:
            from backend.app.billing.model.usage_record import UsageRecord
            from backend.app.llm.presets import get_pricing_map
            from backend.database.db import async_db_session

            agent_map = {cfg['agent_id']: cfg for cfg in agent_configs}
            pricing_map = get_pricing_map()

            async with async_db_session() as db:
                for rec in usage_records:
                    agent_id = rec.get('agent_id')
                    cfg = agent_map.get(agent_id, {}) if agent_id else (agent_configs[0] if agent_configs else {})

                    pt = rec.get('provider_type', cfg.get('provider_type', ''))
                    mn = rec.get('model_name', cfg.get('model_name', ''))
                    prompt_t = rec.get('prompt_tokens', 0)
                    completion_t = rec.get('completion_tokens', 0)
                    cached_t = rec.get('cached_tokens', 0)
                    reasoning_t = rec.get('reasoning_tokens', 0)

                    pricing = pricing_map.get(f'{pt}:{mn}', {})
                    input_price = pricing.get('input_price', 0)
                    cached_price = pricing.get('cached_input_price', input_price * 0.5)
                    output_price = pricing.get('output_price', 0)
                    currency = pricing.get('currency', 'USD')
                    billable_input = prompt_t - cached_t
                    cost = (billable_input * input_price + cached_t * cached_price + completion_t * output_price) / 1_000_000

                    db.add(UsageRecord(
                        user_id=user_id,
                        project_id=project_id,
                        conversation_id=conversation_id,
                        agent_id=agent_id,
                        llm_provider_id=cfg.get('llm_provider_id'),
                        provider_type=pt,
                        model_name=mn,
                        prompt_tokens=prompt_t,
                        completion_tokens=completion_t,
                        total_tokens=rec.get('total_tokens', 0),
                        cached_tokens=cached_t,
                        reasoning_tokens=reasoning_t,
                        estimated_cost=cost,
                        call_type=call_type,
                        status=rec.get('status', 'success'),
                        error_message=rec.get('error_message'),
                        duration_ms=rec.get('duration_ms'),
                        metadata_={
                            'agent_name': rec.get('agent_name') or cfg.get('agent_name'),
                            'role': rec.get('role'),
                            'currency': currency,
                        },
                    ))
                await db.commit()
        except Exception:
            log.exception('Failed to persist usage records')

    @staticmethod
    async def generate_title(
        *,
        project_id: int,
        conversation_id: int,
        user_id: int,
    ) -> str:
        """Use the project's first Agent's LLM to generate a short title for the conversation."""
        from backend.app.conversation.schema.conversation import UpdateConversationParam
        from backend.database.db import async_db_session

        async with async_db_session() as db:
            project, agent_configs, _, _ = await ChatService._get_agents_with_providers(
                db, project_id, user_id, conversation_id=conversation_id,
            )
            if not agent_configs:
                raise errors.RequestError(msg='No Agent available')

            conversation = await conversation_dao.get(db, conversation_id)
            if not conversation or conversation.project_id != project_id:
                raise errors.NotFoundError(msg='Conversation does not exist')

            history = await ChatService._get_history_messages(db, conversation_id, limit=6)
            if not history:
                raise errors.RequestError(msg='Conversation has no messages')

            cfg = agent_configs[0]
            from backend.app.conversation.engine.llm import acompletion

            prompt_messages = [
                {
                    'role': 'system',
                    'content': TITLE_SYSTEM_PROMPT,
                },
                {
                    'role': 'user',
                    'content': '\n'.join(
                        f"{m['role']}: {m['content'][:200]}" for m in history[:4]
                    ),
                },
            ]

            response = await acompletion(
                provider_type=cfg['provider_type'],
                api_base=cfg['api_base'],
                api_key_encrypted=cfg['api_key_encrypted'],
                model_name=cfg['model_name'],
                messages=prompt_messages,
                temperature=0.3,
                max_tokens=50,
            )
            title = (response.choices[0].message.content or '').strip().strip('"\'')
            if not title:
                title = (history[0].get('content', '') or '')[:50]

            from backend.app.conversation.service.conversation_service import conversation_service
            await conversation_service.update(
                db=db, project_id=project_id, pk=conversation_id, user_id=user_id,
                obj=UpdateConversationParam(title=title),
            )

            if response.usage:
                await ChatService._persist_usage_records(
                    user_id=user_id,
                    project_id=project_id,
                    conversation_id=conversation_id,
                    agent_configs=agent_configs,
                    usage_records=[{
                        'provider_type': cfg['provider_type'],
                        'model_name': cfg['model_name'],
                        'prompt_tokens': response.usage.prompt_tokens or 0,
                        'completion_tokens': response.usage.completion_tokens or 0,
                        'total_tokens': response.usage.total_tokens or 0,
                    }],
                    call_type='title_gen',
                )

            await db.commit()
            return title


chat_service: ChatService = ChatService()
