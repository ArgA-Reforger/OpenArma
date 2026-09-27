"""DAG topology graph builder: converts a user-defined JSON topology into an executable LangGraph graph.

Supported node types:
- agent: executes the bound Agent (LLM call + tools)
- coordinator: deeply synthesizes upstream outputs (ForumEngine style)
- aggregator: simple merge/summary of upstream outputs
- condition: routes to different branches based on an expression
- tool: directly executes an MCP or builtin tool
- rag: retrieves from the knowledge base
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from langgraph.graph import END, StateGraph

from backend.app.conversation.engine.graph import (
    AgentConfig,
    ConversationState,
    _agent_llm_with_tool_loop,
    _build_messages_for_agent,
    _build_openai_tools,
    _execute_tool_call,
    _push_event,
    agent_node,
    tool_node,
)
from backend.app.conversation.engine.llm import acompletion

log = logging.getLogger(__name__)


@dataclass
class TopologyNode:
    id: str
    type: str
    agent_id: int | None = None
    config: dict = field(default_factory=dict)
    position: dict = field(default_factory=dict)


@dataclass
class TopologyEdge:
    id: str
    source: str
    target: str
    config: dict = field(default_factory=dict)


class TopologyValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f'Topology validation failed: {"; ".join(errors)}')


def parse_topology(topology: dict) -> tuple[list[TopologyNode], list[TopologyEdge]]:
    nodes = [
        TopologyNode(
            id=n['id'],
            type=n['type'],
            agent_id=int(n['agent_id']) if n.get('agent_id') else None,
            config=n.get('config', {}),
            position=n.get('position', {}),
        )
        for n in topology.get('nodes', [])
    ]
    edges = [
        TopologyEdge(
            id=e['id'],
            source=e['source'],
            target=e['target'],
            config=e.get('config', {}),
        )
        for e in topology.get('edges', [])
    ]
    return nodes, edges


def validate_topology(topology: dict) -> list[str]:
    """Validate topology JSON, return list of error messages (empty = valid)."""
    errors: list[str] = []

    raw_nodes = topology.get('nodes', [])
    raw_edges = topology.get('edges', [])

    if not raw_nodes:
        errors.append('Topology must have at least one node')
        return errors

    node_ids = set()
    for n in raw_nodes:
        if not n.get('id'):
            errors.append('Node missing id')
        if not n.get('type'):
            errors.append(f'Node {n.get("id", "?")} missing type')
        if n.get('type') not in ('agent', 'coordinator', 'aggregator', 'condition', 'tool', 'rag'):
            errors.append(f'Node {n.get("id", "?")} has invalid type: {n.get("type")}')
        if n.get('type') == 'agent' and not n.get('agent_id'):
            errors.append(f'Agent node {n.get("id", "?")} missing agent_id')
        if n['id'] in node_ids:
            errors.append(f'Duplicate node id: {n["id"]}')
        node_ids.add(n['id'])

    for e in raw_edges:
        if not e.get('source') or not e.get('target'):
            errors.append(f'Edge {e.get("id", "?")} missing source or target')
        if e.get('source') not in node_ids:
            errors.append(f'Edge source {e.get("source")} not found in nodes')
        if e.get('target') not in node_ids:
            errors.append(f'Edge target {e.get("target")} not found in nodes')
        if e.get('source') == e.get('target'):
            errors.append(f'Self-loop detected: {e.get("source")}')

    if not _is_dag(node_ids, raw_edges):
        errors.append('Topology contains cycles (must be a DAG)')

    targets = {e['target'] for e in raw_edges}
    roots = node_ids - targets
    if not roots:
        errors.append('No root nodes found (every node has an incoming edge)')

    sources = {e['source'] for e in raw_edges}
    leaves = node_ids - sources
    if not leaves:
        errors.append('No leaf/terminal nodes found')

    return errors


def _is_dag(node_ids: set[str], edges: list[dict]) -> bool:
    in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
    adj: dict[str, list[str]] = {nid: [] for nid in node_ids}

    for e in edges:
        src, tgt = e['source'], e['target']
        if src in adj and tgt in in_degree:
            adj[src].append(tgt)
            in_degree[tgt] += 1

    queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
    visited = 0
    while queue:
        node = queue.popleft()
        visited += 1
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return visited == len(node_ids)


def _topological_sort(nodes: list[TopologyNode], edges: list[TopologyEdge]) -> list[str]:
    in_degree: dict[str, int] = {n.id: 0 for n in nodes}
    adj: dict[str, list[str]] = {n.id: [] for n in nodes}

    for e in edges:
        adj[e.source].append(e.target)
        in_degree[e.target] += 1

    queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
    order: list[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return order


def _get_upstream_nodes(node_id: str, edges: list[TopologyEdge]) -> list[str]:
    return [e.source for e in edges if e.target == node_id]


def _get_downstream_nodes(node_id: str, edges: list[TopologyEdge]) -> list[str]:
    return [e.target for e in edges if e.source == node_id]


def _find_parallel_groups(
    topo_order: list[str],
    edges: list[TopologyEdge],
) -> list[list[str]]:
    """Identify groups of nodes that can execute in parallel (same set of upstream deps)."""
    upstream_map: dict[str, frozenset[str]] = {}
    for nid in topo_order:
        upstream_map[nid] = frozenset(_get_upstream_nodes(nid, edges))

    groups_by_deps: dict[frozenset[str], list[str]] = defaultdict(list)
    for nid in topo_order:
        deps = upstream_map[nid]
        groups_by_deps[deps].append(nid)

    return [group for group in groups_by_deps.values() if len(group) > 1]


def _make_dag_agent_node(
    node: TopologyNode,
    agent_config_map: dict[int, dict],
):
    """Create an async function that executes a single agent within the DAG.
    Uses the shared _agent_llm_with_tool_loop for multi-round tool calling.
    """
    agent_id = node.agent_id
    node_id = node.id

    async def _exec(state: ConversationState) -> dict[str, Any]:
        cfg_dict = agent_config_map.get(agent_id)
        if not cfg_dict:
            log.warning(f'DAG node {node_id}: agent_id {agent_id} not found in configs')
            return {}

        cfg = AgentConfig(**cfg_dict)
        upstream_context = _collect_upstream_context(state, node_id)

        messages = _build_messages_for_agent(
            cfg, state.history, state.user_input, state.rag_context
        )
        if upstream_context:
            messages.append({
                'role': 'user',
                'content': f'Context from previous steps:\n\n{upstream_context}',
            })

        await _push_event(state, {
            'type': 'node_start',
            'node_id': node_id,
            'node_type': 'agent',
            'agent_id': cfg.agent_id,
            'agent_name': cfg.agent_name,
        })

        call_status = 'success'
        error_msg: str | None = None
        t0 = time.monotonic()

        try:
            output_text, usage = await _agent_llm_with_tool_loop(
                cfg, messages, state,
                event_extra={'node_id': node_id, 'agent_id': cfg.agent_id},
            )
        except Exception as e:
            call_status = 'failed'
            error_msg = str(e)[:500]
            output_text = ''
            usage = {}
            log.exception(f'DAG agent node failed: {node_id}')

        duration_ms = int((time.monotonic() - t0) * 1000)

        await _push_event(state, {
            'type': 'usage',
            'node_id': node_id,
            'agent_id': cfg.agent_id,
            'agent_name': cfg.agent_name,
            'model_name': cfg.model_name,
            'provider_type': cfg.provider_type,
            'status': call_status,
            'error_message': error_msg,
            'duration_ms': duration_ms,
            **usage,
        })

        node_outputs = dict(state.node_outputs)
        node_outputs[node_id] = output_text

        agent_outputs = dict(state.agent_outputs)
        agent_outputs[cfg.agent_id] = output_text

        await _push_event(state, {
            'type': 'node_end',
            'node_id': node_id,
            'node_type': 'agent',
            'agent_id': cfg.agent_id,
            'agent_name': cfg.agent_name,
        })

        return {'node_outputs': node_outputs, 'agent_outputs': agent_outputs}

    return _exec


def _collect_upstream_context(state: ConversationState, node_id: str) -> str:
    """Collect outputs from upstream nodes using the topology edges."""
    topology = state.topology or {}
    edges = topology.get('edges', [])
    upstream_ids = [e['source'] for e in edges if e['target'] == node_id]

    if not upstream_ids:
        return ''

    node_map = {n['id']: n for n in topology.get('nodes', [])}
    sections = []
    for uid in upstream_ids:
        output = state.node_outputs.get(uid, '')
        if output:
            n = node_map.get(uid, {})
            label = n.get('config', {}).get('label') or n.get('type', uid)
            sections.append(f'## {label}\n{output}')

    return '\n\n---\n\n'.join(sections)


def _make_dag_coordinator_node(
    node: TopologyNode,
    agent_config_map: dict[int, dict],
):
    """Create a coordinator/aggregator node that synthesizes upstream outputs."""
    node_id = node.id
    merge_strategy = node.config.get('merge_strategy', node.type)

    async def _exec(state: ConversationState) -> dict[str, Any]:
        upstream_context = _collect_upstream_context(state, node_id)
        if not upstream_context:
            return {'node_outputs': {**state.node_outputs, node_id: ''}}

        if merge_strategy == 'passthrough':
            node_outputs = dict(state.node_outputs)
            node_outputs[node_id] = upstream_context
            await _push_event(state, {
                'type': 'node_start', 'node_id': node_id, 'node_type': node.type,
            })
            await _push_event(state, {
                'type': 'token', 'node_id': node_id, 'content': upstream_context,
            })
            await _push_event(state, {
                'type': 'node_end', 'node_id': node_id, 'node_type': node.type,
            })
            return {'node_outputs': node_outputs}

        if merge_strategy == 'aggregator':
            system_msg = (
                'Summarize the following expert analyses into a concise, actionable conclusion. '
                'Preserve key details from each expert.'
            )
            event_prefix = 'aggregator'
        else:
            system_msg = (
                "You are a coordinator synthesizing multiple expert analyses. "
                "Review each expert's output below. Identify key agreements, contradictions, "
                "potential blind spots, and biases. Produce a comprehensive, balanced synthesis "
                "that integrates the strongest insights from all experts."
            )
            event_prefix = 'coordinator'

        custom_prompt = node.config.get('system_prompt')
        if custom_prompt:
            system_msg = custom_prompt

        messages = [
            {'role': 'system', 'content': system_msg},
            {'role': 'user', 'content': f'Here are the expert analyses:\n\n{upstream_context}\n\nPlease synthesize these into a comprehensive response.'},
        ]

        first_agent_cfg = next(iter(agent_config_map.values()), {})
        cfg = AgentConfig(**first_agent_cfg) if first_agent_cfg else AgentConfig()

        await _push_event(state, {
            'type': 'node_start',
            'node_id': node_id,
            'node_type': node.type,
        })
        await _push_event(state, {'type': f'{event_prefix}_start'})

        full_content: list[str] = []
        usage: dict = {}
        call_status = 'success'
        error_msg: str | None = None
        t0 = time.monotonic()

        try:
            response = await acompletion(
                provider_type=cfg.provider_type,
                api_base=cfg.api_base,
                api_key_encrypted=cfg.api_key_encrypted,
                model_name=cfg.model_name,
                messages=messages,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                stream=True,
                stream_options={'include_usage': True},
                provider_id=cfg.llm_provider_id,
                rpm_limit=cfg.rpm_limit,
            )

            async for chunk in response:
                choices = chunk.choices
                if not choices:
                    if hasattr(chunk, 'usage') and chunk.usage:
                        usage = {
                            'prompt_tokens': chunk.usage.prompt_tokens or 0,
                            'completion_tokens': chunk.usage.completion_tokens or 0,
                            'total_tokens': chunk.usage.total_tokens or 0,
                        }
                    continue
                delta = choices[0].delta
                if delta and delta.content:
                    full_content.append(delta.content)
                    await _push_event(state, {
                        'type': 'token',
                        'node_id': node_id,
                        'content': delta.content,
                    })
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = {
                        'prompt_tokens': chunk.usage.prompt_tokens or 0,
                        'completion_tokens': chunk.usage.completion_tokens or 0,
                        'total_tokens': chunk.usage.total_tokens or 0,
                    }

            if not full_content:
                fallback = await acompletion(
                    provider_type=cfg.provider_type,
                    api_base=cfg.api_base,
                    api_key_encrypted=cfg.api_key_encrypted,
                    model_name=cfg.model_name,
                    messages=messages,
                    temperature=cfg.temperature,
                    max_tokens=cfg.max_tokens,
                    stream=False,
                    provider_id=cfg.llm_provider_id,
                    rpm_limit=cfg.rpm_limit,
                )
                content = fallback.choices[0].message.content or ''
                if content:
                    full_content.append(content)
                    await _push_event(state, {
                        'type': 'token', 'node_id': node_id, 'content': content,
                    })
                if fallback.usage:
                    usage = {
                        'prompt_tokens': fallback.usage.prompt_tokens,
                        'completion_tokens': fallback.usage.completion_tokens,
                        'total_tokens': fallback.usage.total_tokens,
                    }
        except Exception as e:
            call_status = 'failed'
            error_msg = str(e)[:500]
            log.exception(f'DAG {event_prefix} node failed: {node_id}')

        duration_ms = int((time.monotonic() - t0) * 1000)

        await _push_event(state, {
            'type': 'usage',
            'node_id': node_id,
            'role': event_prefix,
            'model_name': cfg.model_name,
            'provider_type': cfg.provider_type,
            'status': call_status,
            'error_message': error_msg,
            'duration_ms': duration_ms,
            **usage,
        })

        await _push_event(state, {'type': f'{event_prefix}_end'})
        await _push_event(state, {
            'type': 'node_end', 'node_id': node_id, 'node_type': node.type,
        })

        output_text = ''.join(full_content)
        node_outputs = dict(state.node_outputs)
        node_outputs[node_id] = output_text

        return {'node_outputs': node_outputs, 'response': output_text}

    return _exec


def _make_dag_condition_node(
    node: TopologyNode,
    edges: list[TopologyEdge],
    agent_config_map: dict[int, dict],
):
    """Create a condition node that routes based on LLM evaluation."""
    node_id = node.id
    expression = node.config.get('expression', '')
    downstream = _get_downstream_nodes(node_id, edges)

    async def _exec(state: ConversationState) -> dict[str, Any]:
        upstream_context = _collect_upstream_context(state, node_id)

        await _push_event(state, {
            'type': 'node_start', 'node_id': node_id, 'node_type': 'condition',
        })

        first_cfg = next(iter(agent_config_map.values()), {})
        cfg = AgentConfig(**first_cfg) if first_cfg else AgentConfig()

        target_options = ', '.join(downstream)
        messages = [
            {
                'role': 'system',
                'content': (
                    f'You are a routing decision maker. Based on the context below, '
                    f'decide which path to take. Available targets: {target_options}. '
                    f'Condition: {expression or "Choose the most appropriate target."}. '
                    f'Respond with ONLY the target node ID, nothing else.'
                ),
            },
            {'role': 'user', 'content': upstream_context or state.user_input},
        ]

        try:
            response = await acompletion(
                provider_type=cfg.provider_type,
                api_base=cfg.api_base,
                api_key_encrypted=cfg.api_key_encrypted,
                model_name=cfg.model_name,
                messages=messages,
                temperature=0.1,
                max_tokens=50,
                provider_id=cfg.llm_provider_id,
                rpm_limit=cfg.rpm_limit,
            )
            chosen = (response.choices[0].message.content or '').strip()
            if chosen not in downstream:
                chosen = downstream[0] if downstream else ''
        except Exception:
            log.exception(f'Condition node {node_id} LLM call failed')
            chosen = downstream[0] if downstream else ''

        node_outputs = dict(state.node_outputs)
        node_outputs[node_id] = chosen

        await _push_event(state, {
            'type': 'node_end',
            'node_id': node_id,
            'node_type': 'condition',
            'chosen_target': chosen,
        })

        return {'node_outputs': node_outputs, '_condition_target': chosen}

    return _exec


def _make_dag_tool_node(node: TopologyNode):
    """Create a node that directly executes a tool."""
    node_id = node.id
    tool_name = node.config.get('tool_name', '')
    tool_args = node.config.get('arguments', {})

    async def _exec(state: ConversationState) -> dict[str, Any]:
        await _push_event(state, {
            'type': 'node_start', 'node_id': node_id, 'node_type': 'tool',
        })

        result = await _execute_tool_call(state, tool_name, tool_args)

        node_outputs = dict(state.node_outputs)
        node_outputs[node_id] = result

        await _push_event(state, {
            'type': 'node_end', 'node_id': node_id, 'node_type': 'tool',
        })

        return {'node_outputs': node_outputs}

    return _exec


def _make_dag_rag_node(node: TopologyNode):
    """Create a node that retrieves from knowledge base."""
    node_id = node.id
    kb_ids = node.config.get('kb_ids', [])
    top_k = node.config.get('top_k', 5)

    async def _exec(state: ConversationState) -> dict[str, Any]:
        await _push_event(state, {
            'type': 'node_start', 'node_id': node_id, 'node_type': 'rag',
        })

        try:
            from backend.app.knowledge.service.rag_service import build_rag_context, retrieve_context
            query = state.user_input or ''
            upstream_context = _collect_upstream_context(state, node_id)
            if upstream_context:
                query = f'{query}\n{upstream_context[:500]}'

            results = await retrieve_context(query, kb_ids, top_k=top_k)
            context = build_rag_context(results)
        except Exception:
            log.exception(f'DAG RAG node failed: {node_id}')
            context = ''

        node_outputs = dict(state.node_outputs)
        node_outputs[node_id] = context

        await _push_event(state, {
            'type': 'token', 'node_id': node_id, 'content': context,
        })
        await _push_event(state, {
            'type': 'node_end', 'node_id': node_id, 'node_type': 'rag',
        })

        return {'node_outputs': node_outputs}

    return _exec


def build_dag_graph(
    topology: dict,
    agent_configs: list[dict],
    state: ConversationState,
) -> Any:
    """Build a LangGraph from the user-defined DAG topology.

    The key challenge: LangGraph expects a static graph, but DAG topologies can have
    arbitrary parallel branches. We handle this by:
    1. Using a dispatcher node per "parallel group" that runs nodes concurrently
    2. Sequential nodes are wired directly
    3. Condition nodes use conditional_edges
    """
    nodes, edges = parse_topology(topology)
    topo_order = _topological_sort(nodes, edges)

    node_map = {n.id: n for n in nodes}
    agent_config_map = {cfg['agent_id']: cfg for cfg in agent_configs}

    adj: dict[str, list[str]] = defaultdict(list)
    in_edges: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        adj[e.source].append(e.target)
        in_edges[e.target].append(e.source)

    targets = {e.target for e in edges}
    root_nodes = [nid for nid in topo_order if nid not in targets]
    sources = {e.source for e in edges}
    leaf_nodes = [nid for nid in topo_order if nid not in sources]

    node_funcs: dict[str, Any] = {}
    condition_nodes_set: set[str] = set()

    for n in nodes:
        if n.type == 'agent':
            node_funcs[n.id] = _make_dag_agent_node(n, agent_config_map)
        elif n.type in ('coordinator', 'aggregator'):
            node_funcs[n.id] = _make_dag_coordinator_node(n, agent_config_map)
        elif n.type == 'condition':
            node_funcs[n.id] = _make_dag_condition_node(n, edges, agent_config_map)
            condition_nodes_set.add(n.id)
        elif n.type == 'tool':
            node_funcs[n.id] = _make_dag_tool_node(n)
        elif n.type == 'rag':
            node_funcs[n.id] = _make_dag_rag_node(n)

    parallel_groups: list[tuple[str, list[str], str | None]] = []
    handled_in_parallel: set[str] = set()

    for nid in topo_order:
        downstream = adj.get(nid, [])
        if len(downstream) > 1 and nid not in condition_nodes_set:
            convergence = _find_convergence_point(downstream, adj, leaf_nodes)
            group_id = f'_par_{nid}'
            parallel_groups.append((group_id, downstream, convergence))
            handled_in_parallel.update(downstream)

    graph = StateGraph(ConversationState)

    for nid, func in node_funcs.items():
        graph.add_node(nid, func)

    for group_id, members, convergence in parallel_groups:
        dispatcher = _make_parallel_dispatcher(members, node_funcs)
        graph.add_node(group_id, dispatcher)

    if len(root_nodes) == 1:
        graph.set_entry_point(root_nodes[0])
    else:
        root_dispatcher_id = '_par_root'
        root_dispatcher = _make_parallel_dispatcher(root_nodes, node_funcs)
        graph.add_node(root_dispatcher_id, root_dispatcher)
        graph.set_entry_point(root_dispatcher_id)

        for rn in root_nodes:
            downstream = adj.get(rn, [])
            for d in downstream:
                if d not in handled_in_parallel:
                    graph.add_edge(root_dispatcher_id, d)

        common_downstream = set()
        for rn in root_nodes:
            ds = set(adj.get(rn, []))
            if not common_downstream:
                common_downstream = ds
            else:
                common_downstream &= ds
        if common_downstream:
            for d in common_downstream:
                if d not in handled_in_parallel:
                    graph.add_edge(root_dispatcher_id, d)

    for nid in topo_order:
        if nid in handled_in_parallel:
            continue

        downstream = adj.get(nid, [])

        if nid in condition_nodes_set:
            route_map = {d: d for d in downstream}
            route_map[END] = END

            def _make_condition_router(cond_nid: str, targets: list[str]):
                def _router(state: ConversationState) -> str:
                    chosen = state.node_outputs.get(cond_nid, '')
                    if chosen in targets:
                        return chosen
                    return targets[0] if targets else END
                return _router

            graph.add_conditional_edges(
                nid,
                _make_condition_router(nid, downstream),
                route_map,
            )
            continue

        for group_id, members, convergence in parallel_groups:
            if nid == group_id.replace('_par_', ''):
                graph.add_edge(nid, group_id)
                if convergence:
                    graph.add_edge(group_id, convergence)
                else:
                    graph.add_edge(group_id, END)
                break
        else:
            if not downstream:
                graph.add_edge(nid, END)
            elif len(downstream) == 1:
                target = downstream[0]
                if target not in handled_in_parallel:
                    graph.add_edge(nid, target)

    return graph.compile()


def _find_convergence_point(
    parallel_nodes: list[str],
    adj: dict[str, list[str]],
    leaf_nodes: list[str],
) -> str | None:
    """Find the first common downstream node where parallel branches converge."""
    if not parallel_nodes:
        return None

    def _all_reachable(start: str) -> set[str]:
        visited: set[str] = set()
        queue = deque([start])
        while queue:
            n = queue.popleft()
            for neighbor in adj.get(n, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited

    reachable_sets = [_all_reachable(pn) for pn in parallel_nodes]
    if not reachable_sets:
        return None

    common = reachable_sets[0]
    for rs in reachable_sets[1:]:
        common = common & rs

    if not common:
        return None

    for nid in common:
        if all(nid in rs for rs in reachable_sets):
            return nid

    return None


def _make_parallel_dispatcher(
    node_ids: list[str],
    node_funcs: dict[str, Any],
):
    """Create a dispatcher that runs multiple nodes in parallel via asyncio.gather."""
    async def _dispatch(state: ConversationState) -> dict[str, Any]:
        tasks = []
        for nid in node_ids:
            func = node_funcs.get(nid)
            if func:
                tasks.append(func(state))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        merged_node_outputs = dict(state.node_outputs)
        merged_agent_outputs = dict(state.agent_outputs)

        for result in results:
            if isinstance(result, Exception):
                log.exception('DAG parallel node failed', exc_info=result)
                continue
            if isinstance(result, dict):
                if 'node_outputs' in result:
                    merged_node_outputs.update(result['node_outputs'])
                if 'agent_outputs' in result:
                    merged_agent_outputs.update(result['agent_outputs'])

        return {
            'node_outputs': merged_node_outputs,
            'agent_outputs': merged_agent_outputs,
        }

    return _dispatch
