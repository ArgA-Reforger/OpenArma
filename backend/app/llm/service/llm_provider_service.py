import base64
import hashlib
from typing import Any

import httpx
import litellm
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.llm.crud.crud_llm_provider import llm_provider_dao
from backend.app.llm.model import LLMProvider
from backend.app.llm.schema.llm_provider import (
    CreateLLMProviderParam,
    GetLLMProviderDetail,
    UpdateLLMProviderParam,
    normalize_models,
)
from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.core.conf import settings


def _get_fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.TOKEN_SECRET_KEY.encode()).digest())
    return Fernet(key)


def _encrypt_api_key(plain_key: str) -> str:
    return _get_fernet().encrypt(plain_key.encode()).decode()


def _decrypt_api_key(encrypted_key: str) -> str:
    return _get_fernet().decrypt(encrypted_key.encode()).decode()


def _mask_api_key(encrypted_key: str | None) -> str | None:
    if not encrypted_key:
        return None
    try:
        plain = _decrypt_api_key(encrypted_key)
        if len(plain) >= 4:
            return f'****{plain[-4:]}'
        return '****'
    except Exception:
        return '****'


def _model_to_detail(model: LLMProvider) -> GetLLMProviderDetail:
    return GetLLMProviderDetail(
        id=model.id,
        user_id=model.user_id,
        name=model.name,
        provider_type=model.provider_type,
        api_base=model.api_base,
        api_key_masked=_mask_api_key(model.api_key_encrypted),
        models=normalize_models(model.models),
        is_active=model.is_active,
        visibility=model.visibility,
        created_time=model.created_time,
        updated_time=model.updated_time,
    )


class LLMProviderService:
    @staticmethod
    async def get(*, db: AsyncSession, pk: int, user_id: int) -> GetLLMProviderDetail:
        provider = await llm_provider_dao.get(db, pk)
        if not provider:
            raise errors.NotFoundError(msg='LLM 服务商不存在')
        if provider.user_id != user_id and provider.visibility == 'private':
            raise errors.NotFoundError(msg='LLM 服务商不存在')
        return _model_to_detail(provider)

    @staticmethod
    async def get_list(
        *,
        db: AsyncSession,
        user_id: int,
        name: str | None = None,
        provider_type: str | None = None,
        is_active: bool | None = None,
        visibility: str | None = None,
    ) -> dict[str, Any]:
        select = await llm_provider_dao.get_list(
            user_id=user_id,
            name=name,
            provider_type=provider_type,
            is_active=is_active,
            visibility=visibility,
        )
        page_data = await paging_data(db, select)
        for item in page_data.get('items', []):
            item['api_key_masked'] = _mask_api_key(item.get('api_key_encrypted'))
            item['models'] = normalize_models(item.get('models'))
        return page_data

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateLLMProviderParam, user_id: int) -> int:
        api_key_encrypted = _encrypt_api_key(obj.api_key) if obj.api_key else None
        ins = await llm_provider_dao.create(db, obj, user_id=user_id, api_key_encrypted=api_key_encrypted)
        return ins.id

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateLLMProviderParam, user_id: int) -> int:
        provider = await llm_provider_dao.get(db, pk)
        if not provider:
            raise errors.NotFoundError(msg='LLM 服务商不存在')
        if provider.user_id != user_id:
            raise errors.NotFoundError(msg='LLM 服务商不存在')
        update_data = obj.model_dump(exclude_unset=True, exclude={'api_key'}, mode='json')
        if 'api_key' in obj.model_fields_set:
            update_data['api_key_encrypted'] = _encrypt_api_key(obj.api_key) if obj.api_key else None
        return await llm_provider_dao.update(db, pk, update_data)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int, user_id: int) -> int:
        provider = await llm_provider_dao.get(db, pk)
        if not provider:
            raise errors.NotFoundError(msg='LLM 服务商不存在')
        if provider.user_id != user_id:
            raise errors.NotFoundError(msg='LLM 服务商不存在')
        return await llm_provider_dao.delete(db, pk)

    _EMBEDDING_KEYWORDS = ('embed', 'embedding', 'text-embedding')

    @classmethod
    def _is_embedding_model(cls, model_name: str) -> bool:
        lower = model_name.lower()
        return any(kw in lower for kw in cls._EMBEDDING_KEYWORDS)

    @staticmethod
    async def verify_connection(
        *,
        db: AsyncSession,
        pk: int,
        user_id: int,
        model_name: str,
    ) -> dict[str, Any]:
        provider = await llm_provider_dao.get(db, pk)
        if not provider:
            raise errors.NotFoundError(msg='LLM 服务商不存在')
        if provider.user_id != user_id:
            raise errors.NotFoundError(msg='LLM 服务商不存在')

        try:
            api_key = _decrypt_api_key(provider.api_key_encrypted) if provider.api_key_encrypted else None
        except Exception:
            return {'success': False, 'message': 'API Key 解密失败，请重新设置 API Key'}

        api_base = provider.api_base

        from backend.app.conversation.engine.llm import _build_model_string

        model = _build_model_string(provider.provider_type, model_name)
        is_embedding = LLMProviderService._is_embedding_model(model_name)

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        success = False
        message = ''

        try:
            if is_embedding:
                params: dict = {'model': model, 'input': ['hello']}
                if api_key:
                    params['api_key'] = api_key
                if api_base:
                    params['api_base'] = api_base
                resp = await litellm.aembedding(**params)
                dim = len(resp.data[0]['embedding']) if resp.data else 0
                success = True
                message = f'连接成功 (model={model_name}, embedding dim={dim})'
            else:
                params = {
                    'model': model,
                    'messages': [{'role': 'user', 'content': 'Hi'}],
                    'max_tokens': 5,
                    'temperature': 0,
                    'drop_params': True,
                }
                if api_key:
                    params['api_key'] = api_key
                if api_base:
                    params['api_base'] = api_base
                resp = await litellm.acompletion(**params)
                content = resp.choices[0].message.content or ''
                success = True
                message = f'连接成功 (model={model_name}, reply={content[:50]})'
        except Exception as e:
            message = str(e)[:200]

        models_data = normalize_models(provider.models) or []
        updated = False
        for entry in models_data:
            if entry['name'] == model_name:
                entry['verified_at'] = now.isoformat()
                entry['verified_ok'] = success
                updated = True
                break
        if updated:
            await llm_provider_dao.update(db, pk, {'models': models_data})
            await db.commit()

        return {'success': success, 'message': message}

    @staticmethod
    async def fetch_remote_models(
        *,
        db: AsyncSession,
        pk: int,
        user_id: int,
    ) -> dict[str, Any]:
        provider = await llm_provider_dao.get(db, pk)
        if not provider:
            raise errors.NotFoundError(msg='LLM 服务商不存在')
        if provider.user_id != user_id:
            raise errors.NotFoundError(msg='LLM 服务商不存在')

        try:
            api_key = _decrypt_api_key(provider.api_key_encrypted) if provider.api_key_encrypted else None
        except Exception:
            return {'success': False, 'models': [], 'message': 'API Key 解密失败，请重新设置 API Key'}

        api_base = (provider.api_base or '').rstrip('/')

        if not api_base:
            return {'success': False, 'models': [], 'message': '未配置 API 地址'}

        url = f'{api_base}/models'
        headers: dict[str, str] = {}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            return {'success': False, 'models': [], 'message': str(e)[:200]}

        model_ids: list[str] = []
        items = data.get('data', [])
        if isinstance(items, list):
            for item in items:
                mid = item.get('id') if isinstance(item, dict) else None
                if mid:
                    model_ids.append(mid)

        model_ids.sort()
        return {'success': True, 'models': model_ids, 'message': f'获取到 {len(model_ids)} 个模型'}


llm_provider_service: LLMProviderService = LLMProviderService()
