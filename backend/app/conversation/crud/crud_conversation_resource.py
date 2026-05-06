from sqlalchemy import delete as sa_delete, select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.conversation.model.conversation_resource import ConversationResource


class CRUDConversationResource(CRUDPlus[ConversationResource]):
    async def get_by_conversation(
        self,
        db: AsyncSession,
        conversation_id: int,
        resource_type: str | None = None,
    ) -> list[ConversationResource]:
        stmt = sa_select(self.model).where(self.model.conversation_id == conversation_id)
        if resource_type:
            stmt = stmt.where(self.model.resource_type == resource_type)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_binding(
        self,
        db: AsyncSession,
        conversation_id: int,
        resource_type: str,
        resource_id: int,
    ) -> ConversationResource | None:
        return await self.select_model_by_column(
            db,
            conversation_id=conversation_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )

    async def bind(
        self,
        db: AsyncSession,
        conversation_id: int,
        resource_type: str,
        resource_id: int,
    ) -> ConversationResource:
        instance = self.model(
            conversation_id=conversation_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        db.add(instance)
        await db.flush()
        return instance

    async def unbind(
        self,
        db: AsyncSession,
        conversation_id: int,
        resource_type: str,
        resource_id: int,
    ) -> int:
        result = await db.execute(
            sa_delete(self.model).where(
                self.model.conversation_id == conversation_id,
                self.model.resource_type == resource_type,
                self.model.resource_id == resource_id,
            )
        )
        return result.rowcount


conversation_resource_dao: CRUDConversationResource = CRUDConversationResource(ConversationResource)
