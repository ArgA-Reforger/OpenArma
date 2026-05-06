from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.llm.model import LLMProvider
from backend.app.llm.schema.llm_provider import CreateLLMProviderParam


class CRUDLLMProvider(CRUDPlus[LLMProvider]):
    async def get(self, db: AsyncSession, pk: int) -> LLMProvider | None:
        return await self.select_model_by_column(db, id=pk, del_flag=False)

    async def get_list(
        self,
        user_id: int,
        name: str | None = None,
        provider_type: str | None = None,
        is_active: bool | None = None,
        visibility: str | None = None,
    ) -> Select:
        filters: dict = {'user_id': user_id, 'del_flag': False}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if provider_type is not None:
            filters['provider_type'] = provider_type
        if is_active is not None:
            filters['is_active'] = is_active
        if visibility is not None:
            filters['visibility'] = visibility
        return await self.select_order('id', 'desc', **filters)

    async def create(
        self,
        db: AsyncSession,
        obj: CreateLLMProviderParam,
        user_id: int,
        api_key_encrypted: str | None = None,
    ) -> LLMProvider:
        obj_data = obj.model_dump(exclude={'api_key'}, mode='json')
        obj_data['user_id'] = user_id
        if api_key_encrypted is not None:
            obj_data['api_key_encrypted'] = api_key_encrypted
        ins = self.model(**obj_data)
        db.add(ins)
        await db.flush()
        return ins

    async def update(self, db: AsyncSession, pk: int, update_data: dict) -> int:
        return await self.update_model(db, pk, update_data)

    async def delete(self, db: AsyncSession, pk: int) -> int:
        return await self.delete_model_by_column(db, id=pk, logical_deletion=True, deleted_flag_column='del_flag')


llm_provider_dao: CRUDLLMProvider = CRUDLLMProvider(LLMProvider)
