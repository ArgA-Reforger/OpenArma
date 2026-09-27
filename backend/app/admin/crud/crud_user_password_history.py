from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.user_password_history import UserPasswordHistory
from backend.app.admin.schema.user_password_history import CreateUserPasswordHistoryParam


class CRUDUserPasswordHistory(CRUDPlus[UserPasswordHistory]):
    """User password history database operations"""

    async def create(self, db: AsyncSession, obj: CreateUserPasswordHistoryParam) -> None:
        """
        Create password history record

        :param db: database session
        :param obj: password history record creation params
        :return:
        """
        await self.create_model(db, obj)

    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> Sequence[UserPasswordHistory]:
        """
        Get a user's password history records

        :param db: database session
        :param user_id: user ID
        :return:
        """
        return await self.select_models_order(db, 'id', 'desc', self.model.user_id == user_id)


user_password_history_dao: CRUDUserPasswordHistory = CRUDUserPasswordHistory(UserPasswordHistory)
