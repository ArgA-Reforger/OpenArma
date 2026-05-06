from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.topology.model import Topology
from backend.app.topology.schema.topology import CreateTopologyParam, UpdateTopologyParam


class CRUDTopology(CRUDPlus[Topology]):
    async def get(self, db: AsyncSession, pk: int) -> Topology | None:
        return await self.select_model_by_column(db, id=pk, del_flag=False)

    async def get_list(self, user_id: int, *, visibility: str | None = None) -> Select:
        filters: dict = {'user_id': user_id, 'del_flag': False}
        if visibility is not None:
            filters['visibility'] = visibility
        return await self.select_order('id', 'desc', **filters)

    async def create(self, db: AsyncSession, obj: CreateTopologyParam, user_id: int) -> Topology:
        create_data = obj.model_dump()
        create_data['user_id'] = user_id
        instance = self.model(**create_data)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def update(self, db: AsyncSession, pk: int, obj: UpdateTopologyParam) -> int:
        return await self.update_model(db, pk, obj.model_dump(exclude_unset=True))

    async def delete(self, db: AsyncSession, pk: int) -> int:
        return await self.delete_model_by_column(db, id=pk, logical_deletion=True, deleted_flag_column='del_flag')


topology_dao: CRUDTopology = CRUDTopology(Topology)
