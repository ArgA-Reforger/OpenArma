from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.topology.crud.crud_topology import topology_dao
from backend.app.topology.model import Topology
from backend.app.topology.schema.topology import CreateTopologyParam, UpdateTopologyParam
from backend.common.exception import errors
from backend.common.pagination import paging_data


class TopologyService:
    @staticmethod
    async def get(*, db: AsyncSession, pk: int, user_id: int) -> Topology:
        obj = await topology_dao.get(db, pk)
        if not obj or (obj.user_id != user_id and obj.visibility == 'private'):
            raise errors.NotFoundError(msg='拓扑不存在')
        return obj

    @staticmethod
    async def get_list(*, db: AsyncSession, user_id: int, visibility: str | None = None) -> dict[str, Any]:
        select_stmt = await topology_dao.get_list(user_id=user_id, visibility=visibility)
        return await paging_data(db, select_stmt)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateTopologyParam, user_id: int) -> Topology:
        return await topology_dao.create(db, obj, user_id=user_id)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateTopologyParam, user_id: int) -> int:
        topo = await topology_dao.get(db, pk)
        if not topo or topo.user_id != user_id:
            raise errors.NotFoundError(msg='拓扑不存在')
        return await topology_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int, user_id: int) -> int:
        topo = await topology_dao.get(db, pk)
        if not topo or topo.user_id != user_id:
            raise errors.NotFoundError(msg='拓扑不存在')
        return await topology_dao.delete(db, pk)

    @staticmethod
    async def clone(*, db: AsyncSession, pk: int, user_id: int) -> Topology:
        source = await topology_dao.get(db, pk)
        if not source:
            raise errors.NotFoundError(msg='拓扑不存在')
        if source.user_id != user_id and source.visibility == 'private':
            raise errors.NotFoundError(msg='拓扑不存在')
        clone_data = CreateTopologyParam(
            name=f'{source.name} (Copy)',
            description=source.description,
            topology_json=source.topology_json,
            visibility='private',
        )
        return await topology_dao.create(db, clone_data, user_id=user_id)


topology_service: TopologyService = TopologyService()
