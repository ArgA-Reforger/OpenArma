from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.open.model.arma_config import ArmaConfig
from backend.app.open.schema.arma_config import CreateArmaConfigParam, UpdateArmaConfigParam


class CRUDArmaConfig(CRUDPlus[ArmaConfig]):

    async def get_by_project(self, db: AsyncSession, project_id: int) -> ArmaConfig | None:
        """Get the latest ArmaConfig for a project (newest first)."""
        stmt = sa_select(ArmaConfig).where(
            ArmaConfig.project_id == project_id,
        ).order_by(ArmaConfig.id.desc()).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_by_project(self, db: AsyncSession, project_id: int) -> list[ArmaConfig]:
        """Get all ArmaConfigs for a project."""
        stmt = sa_select(ArmaConfig).where(
            ArmaConfig.project_id == project_id,
        ).order_by(ArmaConfig.id.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_conversation_group(self, db: AsyncSession, conversation_group_id: int) -> ArmaConfig | None:
        """Get ArmaConfig by conversation group ID."""
        return await self.select_model_by_column(db, conversation_group_id=conversation_group_id)

    async def create(self, db: AsyncSession, project_id: int, obj: CreateArmaConfigParam,
                     conversation_group_id: int | None = None) -> ArmaConfig:
        data = obj.model_dump()
        data['project_id'] = project_id
        data['conversation_group_id'] = conversation_group_id
        instance = self.model(**data)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def update(self, db: AsyncSession, pk: int, obj: UpdateArmaConfigParam) -> int:
        return await self.update_model(db, pk, obj.model_dump(exclude_unset=True))

    async def delete(self, db: AsyncSession, pk: int) -> None:
        instance = await self.select_model(db, pk)
        if instance:
            await db.delete(instance)


arma_config_dao: CRUDArmaConfig = CRUDArmaConfig(ArmaConfig)
