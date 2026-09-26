from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.plugin.oauth2.model import UserSocial
from backend.plugin.oauth2.schema.user_social import CreateUserSocialParam


class CRUDUserSocial(CRUDPlus[UserSocial]):
    """User social account database operations"""

    async def check_binding(self, db: AsyncSession, user_id: int, source: str) -> UserSocial | None:
        """
        Check the system user's social account binding

        :param db: Database session
        :param user_id: User ID
        :param source: Social account type
        :return:
        """
        return await self.select_model_by_column(db, user_id=user_id, source=source)

    async def get_by_sid(self, db: AsyncSession, sid: str, source: str) -> UserSocial | None:
        """
        Get a social user by sid

        :param db: Database session
        :param sid: Social account unique ID
        :param source: Social account type
        :return:
        """
        return await self.select_model_by_column(db, sid=sid, source=source)

    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> Sequence[UserSocial]:
        """
        Get all social account bindings by user ID

        :param db: Database session
        :param user_id: User ID
        :return:
        """
        return await self.select_models(db, user_id=user_id)

    async def create(self, db: AsyncSession, obj: CreateUserSocialParam) -> None:
        """
        Create a user social account binding

        :param db: Database session
        :param obj: Create user social account binding parameters
        :return:
        """
        await self.create_model(db, obj)

    async def delete(self, db: AsyncSession, user_id: int, source: str) -> int:
        """
        Delete a user social account binding

        :param db: Database session
        :param user_id: User ID
        :param source: Social account type
        :return:
        """
        return await self.delete_model_by_column(db, user_id=user_id, source=source)

    async def delete_by_user_id(self, db: AsyncSession, user_id: int) -> int:
        """
        Delete user social accounts by user ID

        :param db: Database session
        :param user_id: User ID
        :return:
        """
        return await self.delete_model_by_column(db, user_id=user_id)


user_social_dao: CRUDUserSocial = CRUDUserSocial(UserSocial)
