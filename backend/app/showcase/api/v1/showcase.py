from typing import Annotated

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel
from sqlalchemy import or_, select, update

from backend.app.agent.model import Agent
from backend.app.knowledge.model import KnowledgeBase
from backend.app.llm.model import LLMProvider
from backend.app.llm.schema.llm_provider import normalize_models
from backend.app.mcp.model import MCPServer
from backend.app.topology.model import Topology
from backend.common.exception import errors
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth, DependsSuperUser
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()

RESOURCE_MODEL_MAP = {
    'agents': Agent,
    'knowledge-bases': KnowledgeBase,
    'mcp-servers': MCPServer,
    'llm-providers': LLMProvider,
    'topologies': Topology,
}

VALID_VISIBILITY = {'private', 'public', 'official'}


class SetVisibilityParam(BaseModel):
    visibility: str


@router.get('/agents', summary='公开/官方 Agent 列表', dependencies=[DependsJwtAuth])
async def showcase_agents(
    db: CurrentSession,
    keyword: Annotated[str | None, Query(description='搜索关键词')] = None,
) -> ResponseSchemaModel[list[dict]]:
    stmt = select(Agent).where(
        Agent.del_flag == False,
        or_(Agent.visibility == 'public', Agent.visibility == 'official'),
    )
    if keyword:
        stmt = stmt.where(Agent.name.ilike(f'%{keyword}%'))
    stmt = stmt.order_by(Agent.visibility.desc(), Agent.sort_order, Agent.id.desc())
    result = await db.execute(stmt)
    items = [
        {
            'id': a.id,
            'name': a.name,
            'description': a.description,
            'model_name': a.model_name,
            'visibility': a.visibility,
            'user_id': a.user_id,
        }
        for a in result.scalars().all()
    ]
    return response_base.success(data=items)


@router.get('/knowledge-bases', summary='公开/官方知识库列表', dependencies=[DependsJwtAuth])
async def showcase_knowledge_bases(
    db: CurrentSession,
    keyword: Annotated[str | None, Query(description='搜索关键词')] = None,
) -> ResponseSchemaModel[list[dict]]:
    stmt = select(KnowledgeBase).where(
        KnowledgeBase.del_flag == False,
        or_(KnowledgeBase.visibility == 'public', KnowledgeBase.visibility == 'official'),
    )
    if keyword:
        stmt = stmt.where(KnowledgeBase.name.ilike(f'%{keyword}%'))
    stmt = stmt.order_by(KnowledgeBase.visibility.desc(), KnowledgeBase.id.desc())
    result = await db.execute(stmt)
    items = [
        {
            'id': kb.id,
            'name': kb.name,
            'description': kb.description,
            'embedding_model': kb.embedding_model,
            'document_count': kb.document_count,
            'status': kb.status,
            'visibility': kb.visibility,
            'user_id': kb.user_id,
        }
        for kb in result.scalars().all()
    ]
    return response_base.success(data=items)


@router.get('/mcp-servers', summary='公开/官方 MCP 服务器列表', dependencies=[DependsJwtAuth])
async def showcase_mcp_servers(
    db: CurrentSession,
    keyword: Annotated[str | None, Query(description='搜索关键词')] = None,
) -> ResponseSchemaModel[list[dict]]:
    stmt = select(MCPServer).where(
        MCPServer.del_flag == False,
        or_(MCPServer.visibility == 'public', MCPServer.visibility == 'official'),
    )
    if keyword:
        stmt = stmt.where(MCPServer.name.ilike(f'%{keyword}%'))
    stmt = stmt.order_by(MCPServer.visibility.desc(), MCPServer.id.desc())
    result = await db.execute(stmt)
    items = [
        {
            'id': s.id,
            'name': s.name,
            'description': s.description,
            'transport_type': s.transport_type,
            'is_active': s.is_active,
            'visibility': s.visibility,
            'user_id': s.user_id,
        }
        for s in result.scalars().all()
    ]
    return response_base.success(data=items)


@router.get('/llm-providers', summary='公开/官方 LLM 服务商列表', dependencies=[DependsJwtAuth])
async def showcase_llm_providers(
    db: CurrentSession,
    keyword: Annotated[str | None, Query(description='搜索关键词')] = None,
) -> ResponseSchemaModel[list[dict]]:
    stmt = select(LLMProvider).where(
        LLMProvider.del_flag == False,
        or_(LLMProvider.visibility == 'public', LLMProvider.visibility == 'official'),
    )
    if keyword:
        stmt = stmt.where(LLMProvider.name.ilike(f'%{keyword}%'))
    stmt = stmt.order_by(LLMProvider.visibility.desc(), LLMProvider.id.desc())
    result = await db.execute(stmt)
    items = [
        {
            'id': p.id,
            'name': p.name,
            'provider_type': p.provider_type,
            'api_base': p.api_base,
            'models': normalize_models(p.models),
            'is_active': p.is_active,
            'visibility': p.visibility,
            'user_id': p.user_id,
        }
        for p in result.scalars().all()
    ]
    return response_base.success(data=items)


@router.get('/topologies', summary='公开/官方拓扑列表', dependencies=[DependsJwtAuth])
async def showcase_topologies(
    db: CurrentSession,
    keyword: Annotated[str | None, Query(description='搜索关键词')] = None,
) -> ResponseSchemaModel[list[dict]]:
    stmt = select(Topology).where(
        Topology.del_flag == False,
        or_(Topology.visibility == 'public', Topology.visibility == 'official'),
    )
    if keyword:
        stmt = stmt.where(Topology.name.ilike(f'%{keyword}%'))
    stmt = stmt.order_by(Topology.visibility.desc(), Topology.id.desc())
    result = await db.execute(stmt)
    items = [
        {
            'id': t.id,
            'name': t.name,
            'description': t.description,
            'visibility': t.visibility,
            'user_id': t.user_id,
        }
        for t in result.scalars().all()
    ]
    return response_base.success(data=items)


@router.put(
    '/{resource_type}/{pk}/visibility',
    summary='管理员设置资源可见性',
    dependencies=[DependsSuperUser],
)
async def set_resource_visibility(
    db: CurrentSessionTransaction,
    resource_type: Annotated[str, Path(description='资源类型: agents/knowledge-bases/mcp-servers/llm-providers/topologies')],
    pk: Annotated[int, Path(description='资源 ID')],
    obj: SetVisibilityParam,
) -> ResponseModel:
    model = RESOURCE_MODEL_MAP.get(resource_type)
    if not model:
        raise errors.NotFoundError(msg=f'不支持的资源类型: {resource_type}')
    if obj.visibility not in VALID_VISIBILITY:
        raise errors.RequestError(msg=f'无效的可见性: {obj.visibility}')

    stmt = (
        update(model)
        .where(model.id == pk, model.del_flag == False)  # noqa: E712
        .values(visibility=obj.visibility)
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise errors.NotFoundError(msg='资源不存在')
    return response_base.success()
