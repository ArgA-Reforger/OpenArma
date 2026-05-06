from sqlalchemy import Select, select as sa_select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.agent.model import Agent
from backend.app.agent.schema.agent import CreateAgentParam, UpdateAgentParam


class CRUDAgent(CRUDPlus[Agent]):
    async def get(self, db: AsyncSession, pk: int) -> Agent | None:
        return await self.select_model_by_column(db, id=pk, del_flag=False)

    async def get_default(self, db: AsyncSession, user_id: int) -> Agent | None:
        return await self.select_model_by_column(db, user_id=user_id, is_default=True, del_flag=False)

    async def set_default(self, db: AsyncSession, user_id: int, agent_id: int) -> None:
        """Clear all defaults for user, then set the specified agent as default."""
        await db.execute(
            sa_update(Agent).where(Agent.user_id == user_id, Agent.del_flag == False).values(is_default=False)  # noqa: E712
        )
        await db.execute(
            sa_update(Agent).where(Agent.id == agent_id, Agent.user_id == user_id).values(is_default=True)
        )

    async def get_list(self, user_id: int, *, visibility: str | None = None) -> Select:
        stmt = sa_select(self.model).where(Agent.del_flag == False, Agent.user_id == user_id)  # noqa: E712
        if visibility is not None:
            stmt = stmt.where(Agent.visibility == visibility)
        return stmt.order_by(Agent.sort_order.asc())

    async def create(self, db: AsyncSession, obj: CreateAgentParam, user_id: int) -> Agent:
        create_data = obj.model_dump()
        create_data['user_id'] = user_id
        instance = self.model(**create_data)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def update(self, db: AsyncSession, pk: int, obj: UpdateAgentParam) -> int:
        return await self.update_model(db, pk, obj.model_dump(exclude_unset=True))

    async def delete(self, db: AsyncSession, pk: int) -> int:
        return await self.delete_model_by_column(db, id=pk, logical_deletion=True, deleted_flag_column='del_flag')


agent_dao: CRUDAgent = CRUDAgent(Agent)
