from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.builtin_tool.model import BuiltinTool
from backend.app.builtin_tool.schema.builtin_tool import CreateBuiltinToolParam, UpdateBuiltinToolParam


class CRUDBuiltinTool(CRUDPlus[BuiltinTool]):
    async def get(self, db: AsyncSession, pk: int) -> BuiltinTool | None:
        return await self.select_model_by_column(db, id=pk, del_flag=False)

    async def get_by_name(self, db: AsyncSession, name: str) -> BuiltinTool | None:
        return await self.select_model_by_column(db, name=name, del_flag=False)

    async def get_list(self) -> Select:
        return await self.select_order('created_time', 'desc', del_flag=False)

    async def get_active_list(self, db: AsyncSession, categories: list[str] | None = None) -> list[BuiltinTool]:
        stmt = select(self.model).where(
            self.model.is_active.is_(True),
            self.model.del_flag.is_(False),
        )
        if categories:
            stmt = stmt.where(self.model.category.in_(categories))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, obj: CreateBuiltinToolParam) -> BuiltinTool:
        create_data = obj.model_dump()
        instance = self.model(**create_data)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def update(self, db: AsyncSession, pk: int, obj: UpdateBuiltinToolParam) -> int:
        return await self.update_model(db, pk, obj.model_dump(exclude_unset=True))

    async def delete(self, db: AsyncSession, pk: int) -> int:
        return await self.delete_model_by_column(db, id=pk, logical_deletion=True, deleted_flag_column='del_flag')


builtin_tool_dao: CRUDBuiltinTool = CRUDBuiltinTool(BuiltinTool)
