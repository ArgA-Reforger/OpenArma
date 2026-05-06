from typing import Annotated

from fastapi import APIRouter, Path, Query, Request
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.conversation.model.conversation import Conversation
from backend.app.open.crud.crud_arma_config import arma_config_dao
from backend.app.open.schema.arma_config import (
    CreateArmaConfigParam,
    GetArmaConfigDetail,
    UpdateArmaConfigParam,
)
from backend.app.project.crud.crud_project import project_dao
from backend.common.exception import errors
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession

router = APIRouter(dependencies=[DependsJwtAuth])


async def _find_default_agent(db: AsyncSession, owner_id: int):
    from backend.app.agent.crud.crud_agent import agent_dao
    default_agent = await agent_dao.get_default(db, owner_id)
    if not default_agent:
        from backend.app.agent.model.agent import Agent
        stmt = sa_select(Agent).where(
            Agent.user_id == owner_id,
            Agent.del_flag == False,  # noqa: E712
        ).limit(1)
        result = await db.execute(stmt)
        default_agent = result.scalar_one_or_none()
    return default_agent


async def _sync_arma_conversations(
    db: AsyncSession, project_id: int, owner_id: int,
    sides: list[dict],
    base_conv: Conversation | None = None,
    existing_group_id: int | None = None,
) -> int:
    """Ensure Arma conversations match the faction config within a specific group.
    - base_conv: convert this conversation into the first faction of a *new* group.
    - existing_group_id: scope lookup to this group (for updates to existing groups).
    - Returns conversation_group_id (the primary conversation's ID)."""
    all_factions = [s['faction'] for s in sides]
    llm_factions = {s['faction'] for s in sides if s.get('control') == 'llm'}
    default_agent = await _find_default_agent(db, owner_id)

    group_conv_id: int | None = existing_group_id
    assigned_base = False

    for faction in all_factions:
        stmt = sa_select(Conversation).where(
            Conversation.project_id == project_id,
            Conversation.source == 'arma',
            Conversation.status == 'active',
            Conversation.side == faction,
            Conversation.del_flag == False,  # noqa: E712
        )
        if existing_group_id:
            stmt = stmt.where(Conversation.conversation_group_id == existing_group_id)
        elif base_conv:
            stmt = stmt.where(Conversation.id == base_conv.id)
        stmt = stmt.limit(1)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            if group_conv_id is None:
                group_conv_id = existing.id
            if existing.agent_id is None and faction in llm_factions and default_agent:
                existing.agent_id = default_agent.id
        elif base_conv and not assigned_base:
            base_conv.source = 'arma'
            base_conv.side = faction
            base_conv.title = f'Arma Commander - {faction}'
            if base_conv.agent_id is None and faction in llm_factions and default_agent:
                base_conv.agent_id = default_agent.id
            assigned_base = True
            await db.flush()
            if group_conv_id is None:
                group_conv_id = base_conv.id
            base_conv.conversation_group_id = group_conv_id
        else:
            conv = Conversation(
                project_id=project_id,
                user_id=owner_id,
                title=f'Arma Commander - {faction}',
                source='arma',
                side=faction,
                status='active',
                conversation_group_id=group_conv_id,
                agent_id=default_agent.id if (default_agent and faction in llm_factions) else None,
            )
            db.add(conv)
            await db.flush()
            if group_conv_id is None:
                group_conv_id = conv.id
                conv.conversation_group_id = group_conv_id

    if group_conv_id and not existing_group_id:
        first_conv = await db.get(Conversation, group_conv_id)
        if first_conv and first_conv.conversation_group_id != group_conv_id:
            first_conv.conversation_group_id = group_conv_id

    faction_set = set(all_factions)
    if existing_group_id:
        stale_stmt = sa_select(Conversation).where(
            Conversation.project_id == project_id,
            Conversation.source == 'arma',
            Conversation.status == 'active',
            Conversation.conversation_group_id == existing_group_id,
            Conversation.del_flag == False,  # noqa: E712
        )
        stale_result = await db.execute(stale_stmt)
        for conv in stale_result.scalars().all():
            if conv.side and conv.side not in faction_set:
                conv.status = 'archived'

    await db.flush()
    return group_conv_id or 0


async def _verify_project_owner(db: CurrentSession, request: Request, project_id: int):
    project = await project_dao.get(db, project_id)
    if not project or project.owner_id != request.user.id:
        raise errors.NotFoundError(msg='Project not found')
    return project


async def _resolve_config(db: CurrentSession, project_id: int, group_id: int | None):
    """Resolve ArmaConfig strictly by conversation_group_id. Returns None if group_id absent."""
    if group_id:
        config = await arma_config_dao.get_by_conversation_group(db, group_id)
        if config and config.project_id == project_id:
            return config
    return None


@router.get('/{project_id}/arma-configs')
async def list_arma_configs(
    db: CurrentSession,
    request: Request,
    project_id: Annotated[int, Path(description='Project ID')],
) -> ResponseSchemaModel:
    """List all ArmaConfigs for a project."""
    await _verify_project_owner(db, request, project_id)
    configs = await arma_config_dao.get_all_by_project(db, project_id)
    data = [GetArmaConfigDetail.model_validate(c).model_dump() for c in configs]
    return response_base.success(data=data)


@router.get('/{project_id}/arma-config')
async def get_arma_config(
    db: CurrentSession,
    request: Request,
    project_id: Annotated[int, Path(description='Project ID')],
    group_id: Annotated[int | None, Query(description='Conversation group ID')] = None,
) -> ResponseSchemaModel:
    await _verify_project_owner(db, request, project_id)
    config = await _resolve_config(db, project_id, group_id)
    if not config:
        return response_base.success(data=None)
    return response_base.success(data=GetArmaConfigDetail.model_validate(config).model_dump())


@router.post('/{project_id}/arma-config')
async def create_arma_config(
    db: CurrentSession,
    request: Request,
    project_id: Annotated[int, Path(description='Project ID')],
    obj: CreateArmaConfigParam,
    conversation_id: Annotated[int | None, Query(description='Base conversation to convert')] = None,
) -> ResponseSchemaModel:
    """Create Arma config. If conversation_id is given, that conversation becomes the
    primary Arma conversation (source=arma, side=first faction)."""
    project = await _verify_project_owner(db, request, project_id)
    sides = [s.model_dump() for s in obj.sides] if obj.sides else []

    base_conv = None
    if conversation_id:
        base_conv = await db.get(Conversation, conversation_id)
        if not base_conv or base_conv.project_id != project.id:
            raise errors.NotFoundError(msg='Conversation not found')
        existing = await arma_config_dao.get_by_conversation_group(db, conversation_id)
        if existing:
            raise errors.ForbiddenError(msg='This conversation group already has an Arma config')

    group_id = await _sync_arma_conversations(db, project_id, project.owner_id, sides, base_conv)
    config = await arma_config_dao.create(db, project_id, obj, conversation_group_id=group_id)
    await db.commit()
    await db.refresh(config)
    return response_base.success(data=GetArmaConfigDetail.model_validate(config).model_dump())


@router.put('/{project_id}/arma-config')
async def update_arma_config(
    db: CurrentSession,
    request: Request,
    project_id: Annotated[int, Path(description='Project ID')],
    obj: UpdateArmaConfigParam,
    group_id: Annotated[int | None, Query(description='Conversation group ID')] = None,
) -> ResponseSchemaModel:
    project = await _verify_project_owner(db, request, project_id)
    config = await _resolve_config(db, project_id, group_id)
    if not config:
        raise errors.NotFoundError(msg='Arma config not found')
    if obj.running is True:
        all_configs = await arma_config_dao.get_all_by_project(db, project_id)
        for other in all_configs:
            if other.id != config.id and other.running:
                other.running = False
        await db.flush()
    await arma_config_dao.update(db, config.id, obj)
    if obj.sides is not None:
        sides = [s.model_dump() for s in obj.sides]
        new_group_id = await _sync_arma_conversations(
            db, project_id, project.owner_id, sides,
            existing_group_id=config.conversation_group_id,
        )
        if new_group_id and config.conversation_group_id != new_group_id:
            config.conversation_group_id = new_group_id
            await db.flush()
    await db.commit()
    updated = await _resolve_config(db, project_id, config.conversation_group_id)
    return response_base.success(data=GetArmaConfigDetail.model_validate(updated).model_dump())


@router.delete('/{project_id}/arma-config')
async def delete_arma_config(
    db: CurrentSession,
    request: Request,
    project_id: Annotated[int, Path(description='Project ID')],
    group_id: Annotated[int | None, Query(description='Conversation group ID')] = None,
) -> ResponseSchemaModel:
    await _verify_project_owner(db, request, project_id)
    config = await _resolve_config(db, project_id, group_id)
    if not config:
        raise errors.NotFoundError(msg='Arma config not found')
    await arma_config_dao.delete(db, config.id)
    await db.commit()
    return response_base.success()
