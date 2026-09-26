import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.core.conf import settings
from backend.database.redis import redis_client
from backend.plugin.oauth2.crud.crud_user_social import user_social_dao
from backend.plugin.oauth2.enums import UserSocialAuthType, UserSocialType
from backend.plugin.oauth2.schema.user_social import CreateUserSocialParam


class UserSocialService:
    @staticmethod
    async def get_bindings(*, db: AsyncSession, user_id: int) -> list[str]:
        """
        Get the social accounts already bound to the user

        :param db: Database session
        :param user_id: User ID
        :return: List of bindings, each item containing sid, source, etc.
        """
        bindings = await user_social_dao.get_by_user_id(db, user_id)
        return [binding.source for binding in bindings]

    @staticmethod
    async def binding_with_oauth2(
        *,
        db: AsyncSession,
        user_id: int,
        sid: str,
        source: UserSocialType,
    ) -> None:
        """
        Bind a user's social account through the OAuth2 flow

        :param db: Database session
        :param user_id: User ID
        :param sid: Social account unique ID
        :param source: Binding source
        :return:
        """
        if await user_social_dao.check_binding(db, user_id, source.value):
            raise errors.RequestError(msg=f'User has already bound a {source.value} account')

        if await user_social_dao.get_by_sid(db, sid, source.value):
            raise errors.RequestError(msg=f'This {source.value} account is already bound to another user')

        new_user_social = CreateUserSocialParam(sid=sid, source=source.value, user_id=user_id)
        await user_social_dao.create(db, new_user_social)

    @staticmethod
    async def unbinding(*, db: AsyncSession, user_id: int, source: UserSocialType) -> int:
        """
        Unbind a user's social account

        :param db: Database session
        :param user_id: User ID
        :param source: Unbinding source
        :return:
        """
        bind = await user_social_dao.check_binding(db, user_id, source.value)
        if not bind:
            raise errors.NotFoundError(msg=f'User has not bound a {source.value} account')
        return await user_social_dao.delete(db, user_id, source.value)

    @staticmethod
    async def get_binding_auth_url(*, user_id: int, source: UserSocialType) -> str:
        state = str(uuid.uuid4())

        await redis_client.setex(
            f'{settings.OAUTH2_STATE_REDIS_PREFIX}:{state}',
            settings.OAUTH2_STATE_EXPIRE_SECONDS,
            json.dumps({'type': UserSocialAuthType.binding.value, 'user_id': user_id}),
        )

        match source:
            case UserSocialType.github:
                from backend.plugin.oauth2.api.v1.github import github_client

                auth_url = await github_client.get_authorization_url(
                    redirect_uri=settings.OAUTH2_GITHUB_REDIRECT_URI,
                    state=state,
                )
            case UserSocialType.google:
                from backend.plugin.oauth2.api.v1.google import google_client

                auth_url = await google_client.get_authorization_url(
                    redirect_uri=settings.OAUTH2_GOOGLE_REDIRECT_URI,
                    state=state,
                )
            case _:
                raise errors.ForbiddenError(msg=f'Binding for {source} is not supported yet')

        return auth_url


user_social_service: UserSocialService = UserSocialService()
