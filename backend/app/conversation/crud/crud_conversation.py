from sqlalchemy import Select, select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.conversation.model import Conversation
from backend.app.conversation.schema.conversation import CreateConversationParam, UpdateConversationParam


class CRUDConversation(CRUDPlus[Conversation]):
    async def get(self, db: AsyncSession, pk: int) -> Conversation | None:
        return await self.select_model_by_column(db, id=pk, del_flag=False)

    async def get_list(
        self,
        project_id: int,
        user_id: int | None = None,
        status: str | None = None,
    ) -> Select:
        stmt = sa_select(self.model).where(
            self.model.project_id == project_id,
            self.model.del_flag == False,  # noqa: E712
        )
        if user_id is not None:
            stmt = stmt.where(self.model.user_id == user_id)
        if status is not None:
            stmt = stmt.where(self.model.status == status)
        return stmt.order_by(self.model.is_pinned.desc(), self.model.id.desc())

    async def update(self, db: AsyncSession, pk: int, obj: UpdateConversationParam) -> int:
        return await self.update_model(db, pk, obj)

    async def create(
        self,
        db: AsyncSession,
        obj: CreateConversationParam,
        project_id: int,
        user_id: int | None = None,
    ) -> Conversation:
        data = obj.model_dump()
        data['project_id'] = project_id
        data['user_id'] = user_id
        instance = self.model(**data)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def get_by_share_code(self, db: AsyncSession, share_code: str) -> Conversation | None:
        return await self.select_model_by_column(db, share_code=share_code, del_flag=False)

    async def get_by_group_id(self, db: AsyncSession, group_id: int) -> list[Conversation]:
        stmt = sa_select(self.model).where(
            self.model.conversation_group_id == group_id,
            self.model.del_flag == False,  # noqa: E712
        ).order_by(self.model.id.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, db: AsyncSession, pk: int) -> int:
        return await self.delete_model_by_column(db, id=pk, logical_deletion=True, deleted_flag_column='del_flag')


conversation_dao: CRUDConversation = CRUDConversation(Conversation)
