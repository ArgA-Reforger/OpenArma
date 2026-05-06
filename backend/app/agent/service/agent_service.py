from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent.crud.crud_agent import agent_dao
from backend.app.agent.model import Agent
from backend.app.agent.schema.agent import CreateAgentParam, UpdateAgentParam
from backend.common.exception import errors
from backend.common.pagination import paging_data


class AgentService:
    @staticmethod
    async def get(*, db: AsyncSession, pk: int, user_id: int) -> Agent:
        obj = await agent_dao.get(db, pk)
        if not obj or (obj.user_id != user_id and obj.visibility == 'private'):
            raise errors.NotFoundError(msg='Agent 不存在')
        return obj

    @staticmethod
    async def get_list(*, db: AsyncSession, user_id: int, visibility: str | None = None) -> dict[str, Any]:
        agent_select = await agent_dao.get_list(user_id=user_id, visibility=visibility)
        return await paging_data(db, agent_select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateAgentParam, user_id: int) -> Agent:
        return await agent_dao.create(db, obj, user_id=user_id)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateAgentParam, user_id: int) -> int:
        agent = await agent_dao.get(db, pk)
        if not agent or agent.user_id != user_id:
            raise errors.NotFoundError(msg='Agent 不存在')
        return await agent_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int, user_id: int) -> int:
        agent = await agent_dao.get(db, pk)
        if not agent or agent.user_id != user_id:
            raise errors.NotFoundError(msg='Agent 不存在')
        return await agent_dao.delete(db, pk)

    @staticmethod
    async def set_default(*, db: AsyncSession, pk: int, user_id: int) -> None:
        agent = await agent_dao.get(db, pk)
        if not agent or agent.user_id != user_id:
            raise errors.NotFoundError(msg='Agent 不存在')
        await agent_dao.set_default(db, user_id=user_id, agent_id=pk)

    @staticmethod
    async def clone(*, db: AsyncSession, pk: int, user_id: int) -> Agent:
        source = await agent_dao.get(db, pk)
        if not source:
            raise errors.NotFoundError(msg='Agent 不存在')
        if source.user_id != user_id and source.visibility == 'private':
            raise errors.NotFoundError(msg='Agent 不存在')
        clone_data = CreateAgentParam(
            name=f'{source.name} (Copy)',
            description=source.description,
            system_prompt=source.system_prompt,
            rules=source.rules,
            skills=source.skills,
            llm_provider_id=source.llm_provider_id if source.user_id == user_id else None,
            model_name=source.model_name,
            temperature=source.temperature,
            top_p=source.top_p,
            max_tokens=source.max_tokens,
            presence_penalty=source.presence_penalty,
            frequency_penalty=source.frequency_penalty,
            sort_order=0,
            visibility='private',
            builtin_tools=source.builtin_tools,
            enable_sub_agents=source.enable_sub_agents,
        )
        return await agent_dao.create(db, clone_data, user_id=user_id)


agent_service: AgentService = AgentService()
