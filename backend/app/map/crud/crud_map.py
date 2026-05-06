from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.map.model.map import GameMap, MapEntity, MapLandmark, MapLayer, MapRoad, MapZone
from backend.app.map.schema.map import (
    CreateLandmarkParam,
    CreateRoadParam,
    CreateZoneParam,
    UpdateLandmarkParam,
    UpdateLayerParam,
    UpdateMapParam,
    UpdateZoneParam,
)


class CRUDMap(CRUDPlus[GameMap]):
    async def get(self, db: AsyncSession, pk: int) -> GameMap | None:
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> GameMap | None:
        return await self.select_model_by_column(db, name=name)

    async def get_list(
        self,
        db: AsyncSession,
        status: str | None = None,
        source: str | None = None,
    ) -> list[GameMap]:
        stmt = select(GameMap)
        if status:
            stmt = stmt.where(GameMap.status == status)
        if source:
            stmt = stmt.where(GameMap.source == source)
        stmt = stmt.order_by(GameMap.created_time.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, **kwargs) -> GameMap:
        instance = GameMap(**kwargs)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def update(self, db: AsyncSession, pk: int, obj: UpdateMapParam) -> int:
        return await self.update_model(db, pk, obj.model_dump(exclude_unset=True))

    async def delete(self, db: AsyncSession, pk: int) -> None:
        obj = await self.get(db, pk)
        if obj:
            await db.delete(obj)


class CRUDLandmark(CRUDPlus[MapLandmark]):
    async def get(self, db: AsyncSession, pk: int) -> MapLandmark | None:
        return await self.select_model(db, pk)

    async def get_by_map(
        self,
        db: AsyncSession,
        map_id: int,
        type_filter: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MapLandmark]:
        stmt = select(MapLandmark).where(MapLandmark.map_id == map_id)
        if type_filter:
            stmt = stmt.where(MapLandmark.type == type_filter)
        stmt = stmt.offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create(self, db: AsyncSession, items: list[MapLandmark]) -> int:
        db.add_all(items)
        await db.flush()
        return len(items)

    async def create_single(self, db: AsyncSession, map_id: int, obj: CreateLandmarkParam) -> MapLandmark:
        item = MapLandmark(
            map_id=map_id,
            name=obj.name,
            type=obj.type,
            position_x=obj.position_x,
            position_z=obj.position_z,
            position_y=obj.position_y,
            tactical_description=obj.description,
            tags=obj.tags,
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item

    async def delete_single(self, db: AsyncSession, pk: int) -> None:
        item = await self.get(db, pk)
        if item:
            await db.delete(item)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateLandmarkParam) -> int:
        return await self.update_model(db, pk, obj.model_dump(exclude_unset=True))

    async def delete_by_map(self, db: AsyncSession, map_id: int) -> int:
        stmt = delete(MapLandmark).where(MapLandmark.map_id == map_id)
        result = await db.execute(stmt)
        return result.rowcount


class CRUDRoad(CRUDPlus[MapRoad]):
    async def get_by_map(self, db: AsyncSession, map_id: int) -> list[MapRoad]:
        stmt = select(MapRoad).where(MapRoad.map_id == map_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_single(self, db: AsyncSession, map_id: int, obj: CreateRoadParam, length: float = 0) -> MapRoad:
        item = MapRoad(
            map_id=map_id,
            name=obj.name,
            type=obj.type,
            width=obj.width,
            points=obj.points,
            length=length,
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item

    async def delete_single(self, db: AsyncSession, pk: int) -> None:
        stmt = select(MapRoad).where(MapRoad.id == pk)
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        if item:
            await db.delete(item)

    async def bulk_create(self, db: AsyncSession, items: list[MapRoad]) -> int:
        db.add_all(items)
        await db.flush()
        return len(items)

    async def delete_by_map(self, db: AsyncSession, map_id: int) -> int:
        stmt = delete(MapRoad).where(MapRoad.map_id == map_id)
        result = await db.execute(stmt)
        return result.rowcount


class CRUDZone(CRUDPlus[MapZone]):
    async def get_by_map(self, db: AsyncSession, map_id: int) -> list[MapZone]:
        stmt = select(MapZone).where(MapZone.map_id == map_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_single(self, db: AsyncSession, map_id: int, obj: CreateZoneParam) -> MapZone:
        item = MapZone(
            map_id=map_id,
            name=obj.name,
            type=obj.type,
            center_x=obj.center_x,
            center_z=obj.center_z,
            radius=obj.radius,
            boundary=obj.boundary,
            tactical_notes=obj.tactical_notes,
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item

    async def delete_single(self, db: AsyncSession, pk: int) -> None:
        stmt = select(MapZone).where(MapZone.id == pk)
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        if item:
            await db.delete(item)

    async def bulk_create(self, db: AsyncSession, items: list[MapZone]) -> int:
        db.add_all(items)
        await db.flush()
        return len(items)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateZoneParam) -> int:
        return await self.update_model(db, pk, obj.model_dump(exclude_unset=True))

    async def delete_by_map(self, db: AsyncSession, map_id: int) -> int:
        stmt = delete(MapZone).where(MapZone.map_id == map_id)
        result = await db.execute(stmt)
        return result.rowcount


class CRUDEntity(CRUDPlus[MapEntity]):
    async def get_by_map(
        self,
        db: AsyncSession,
        map_id: int,
        category: str | None = None,
        chunk_name: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MapEntity]:
        stmt = select(MapEntity).where(MapEntity.map_id == map_id)
        if category:
            stmt = stmt.where(MapEntity.category == category)
        if chunk_name:
            stmt = stmt.where(MapEntity.chunk_name == chunk_name)
        stmt = stmt.offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create(self, db: AsyncSession, items: list[MapEntity]) -> int:
        db.add_all(items)
        await db.flush()
        return len(items)

    async def count_by_map(self, db: AsyncSession, map_id: int) -> int:
        from sqlalchemy import func
        stmt = select(func.count(MapEntity.id)).where(MapEntity.map_id == map_id)
        result = await db.execute(stmt)
        return result.scalar_one()

    async def delete_by_map(self, db: AsyncSession, map_id: int) -> int:
        stmt = delete(MapEntity).where(MapEntity.map_id == map_id)
        result = await db.execute(stmt)
        return result.rowcount


class CRUDLayer(CRUDPlus[MapLayer]):
    async def get(self, db: AsyncSession, pk: int) -> MapLayer | None:
        return await self.select_model(db, pk)

    async def get_by_map(self, db: AsyncSession, map_id: int) -> list[MapLayer]:
        stmt = select(MapLayer).where(MapLayer.map_id == map_id).order_by(MapLayer.z_index)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, **kwargs) -> MapLayer:
        instance = MapLayer(**kwargs)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def update(self, db: AsyncSession, pk: int, obj: UpdateLayerParam) -> int:
        return await self.update_model(db, pk, obj.model_dump(exclude_unset=True))

    async def delete(self, db: AsyncSession, pk: int) -> None:
        obj = await self.get(db, pk)
        if obj:
            await db.delete(obj)

    async def delete_by_map(self, db: AsyncSession, map_id: int) -> int:
        stmt = delete(MapLayer).where(MapLayer.map_id == map_id)
        result = await db.execute(stmt)
        return result.rowcount


map_dao: CRUDMap = CRUDMap(GameMap)
layer_dao: CRUDLayer = CRUDLayer(MapLayer)
landmark_dao: CRUDLandmark = CRUDLandmark(MapLandmark)
entity_dao: CRUDEntity = CRUDEntity(MapEntity)
road_dao: CRUDRoad = CRUDRoad(MapRoad)
zone_dao: CRUDZone = CRUDZone(MapZone)
