from typing import Any

import bcrypt

from sqlalchemy import Select, delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus, JoinConfig

from backend.app.admin.model import (
    DataRule,
    DataScope,
    Dept,
    Menu,
    Role,
    User,
    data_scope_rule,
    role_data_scope,
    role_menu,
    user_role,
)
from backend.app.admin.schema.user import (
    AddOAuth2UserParam,
    AddUserParam,
    AddUserRoleParam,
    UpdateUserParam,
)
from backend.app.admin.utils.password_security import get_hash_password
from backend.utils.dynamic_import import import_module_cached
from backend.utils.serializers import select_join_serialize
from backend.utils.timezone import timezone


class CRUDUser(CRUDPlus[User]):
    """User database operations"""

    async def get(self, db: AsyncSession, user_id: int) -> User | None:
        """
        Get user details

        :param db: database session
        :param user_id: user ID
        :return:
        """
        return await self.select_model(db, user_id)

    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        """
        Get a user by username

        :param db: database session
        :param username: username
        :return:
        """
        return await self.select_model_by_column(db, username=username)

    async def get_by_nickname(self, db: AsyncSession, nickname: str) -> User | None:
        """
        Get a user by nickname

        :param db: database session
        :param nickname: nickname
        :return:
        """
        return await self.select_model_by_column(db, nickname=nickname)

    async def check_email(self, db: AsyncSession, email: str) -> User | None:
        """
        Check whether an email is already bound

        :param db: database session
        :param email: email address
        :return:
        """
        return await self.select_model_by_column(db, email=email)

    async def get_select(self, dept: int | None, username: str | None, phone: str | None, status: int | None) -> Select:
        """
        Get the query expression for the user list

        :param dept: department ID
        :param username: username
        :param phone: phone number
        :param status: user status
        :return:
        """
        filters = {}

        if dept:
            filters['dept_id'] = dept
        if username:
            filters['username__like'] = f'%{username}%'
        if phone:
            filters['phone__like'] = f'%{phone}%'
        if status is not None:
            filters['status'] = status

        return await self.select_order(
            'id',
            'desc',
            join_conditions=[
                JoinConfig(model=Dept, join_on=Dept.id == self.model.dept_id, fill_result=True),
                JoinConfig(model=user_role, join_on=user_role.c.user_id == self.model.id),
                JoinConfig(model=Role, join_on=Role.id == user_role.c.role_id, fill_result=True),
            ],
            **filters,
        )

    async def add(self, db: AsyncSession, obj: AddUserParam) -> None:
        """
        Add user

        :param db: database session
        :param obj: user creation params
        :return:
        """
        salt = bcrypt.gensalt()
        obj.password = get_hash_password(obj.password, salt)

        dict_obj = obj.model_dump(exclude={'roles'})
        dict_obj.update({'salt': salt})
        new_user = self.model(**dict_obj)
        db.add(new_user)
        await db.flush()

        if obj.roles:
            role_stmt = select(Role).where(Role.id.in_(obj.roles))
            result = await db.execute(role_stmt)
            roles = result.scalars().all()

            user_role_data = [AddUserRoleParam(user_id=new_user.id, role_id=role.id).model_dump() for role in roles]
            user_role_stmt = insert(user_role)
            await db.execute(user_role_stmt, user_role_data)

    async def add_by_oauth2(self, db: AsyncSession, obj: AddOAuth2UserParam) -> None:
        """
        Add a user via OAuth2

        :param db: database session
        :param obj: user registration params
        :return:
        """
        dict_obj = obj.model_dump()
        dict_obj.update({'is_staff': False, 'salt': None})
        new_user = self.model(**dict_obj)
        db.add(new_user)
        await db.flush()

        role_stmt = select(Role)
        result = await db.execute(role_stmt)
        role = result.scalars().first()  # Bind the first role by default

        user_role_stmt = insert(user_role).values(AddUserRoleParam(user_id=new_user.id, role_id=role.id).model_dump())
        await db.execute(user_role_stmt)

    async def update(self, db: AsyncSession, user_id: int, obj: UpdateUserParam) -> int:
        """
        Update user info

        :param db: database session
        :param user_id: user ID
        :param obj: user update params
        :return:
        """
        role_ids = obj.roles
        del obj.roles

        count = await self.update_model(db, user_id, obj)

        user_role_stmt = delete(user_role).where(user_role.c.user_id == user_id)
        await db.execute(user_role_stmt)

        if role_ids:
            role_stmt = select(Role).where(Role.id.in_(role_ids))
            result = await db.execute(role_stmt)
            roles = result.scalars().all()

            user_role_data = [AddUserRoleParam(user_id=user_id, role_id=role.id).model_dump() for role in roles]
            user_role_stmt = insert(user_role)
            await db.execute(user_role_stmt, user_role_data)

        return count

    async def update_login_time(self, db: AsyncSession, username: str) -> int:
        """
        Update the user's last login time

        :param db: database session
        :param username: username
        :return:
        """
        return await self.update_model_by_column(db, {'last_login_time': timezone.now()}, username=username)

    async def update_password_changed_time(self, db: AsyncSession, user_id: int) -> int:
        """
        Update the user's last password-changed time

        :param db: database session
        :param user_id: user ID
        :return:
        """
        return await self.update_model(db, user_id, {'last_password_changed_time': timezone.now()})

    async def update_nickname(self, db: AsyncSession, user_id: int, nickname: str) -> int:
        """
        Update user nickname

        :param db: database session
        :param user_id: user ID
        :param nickname: nickname
        :return:
        """
        return await self.update_model(db, user_id, {'nickname': nickname})

    async def update_avatar(self, db: AsyncSession, user_id: int, avatar: str) -> int:
        """
        Update user avatar

        :param db: database session
        :param user_id: user ID
        :param avatar: avatar URL
        :return:
        """
        return await self.update_model(db, user_id, {'avatar': avatar})

    async def update_email(self, db: AsyncSession, user_id: int, email: str) -> int:
        """
        Update user email

        :param db: database session
        :param user_id: user ID
        :param email: email address
        :return:
        """
        return await self.update_model(db, user_id, {'email': email})

    async def reset_password(self, db: AsyncSession, pk: int, password: str) -> int:
        """
        Reset user password

        :param db: database session
        :param pk: user ID
        :param password: new password
        :return:
        """
        salt = bcrypt.gensalt()
        new_pwd = get_hash_password(password, salt)
        return await self.update_model(db, pk, {'password': new_pwd, 'salt': salt}, flush=True)

    async def set_super(self, db: AsyncSession, user_id: int, *, is_super: bool) -> int:
        """
        Set the user's superuser status

        :param db: database session
        :param user_id: user ID
        :param is_super: whether the user is a superuser
        :return:
        """
        return await self.update_model(db, user_id, {'is_superuser': is_super})

    async def set_staff(self, db: AsyncSession, user_id: int, *, is_staff: bool) -> int:
        """
        Set the user's backend login status

        :param db: database session
        :param user_id: user ID
        :param is_staff: whether the user can log in to the backend
        :return:
        """
        return await self.update_model(db, user_id, {'is_staff': is_staff})

    async def set_status(self, db: AsyncSession, user_id: int, status: int) -> int:
        """
        Set user status

        :param db: database session
        :param user_id: user ID
        :param status: status
        :return:
        """
        return await self.update_model(db, user_id, {'status': status})

    async def set_multi_login(self, db: AsyncSession, user_id: int, *, multi_login: bool) -> int:
        """
        Set the user's multi-device login status

        :param db: database session
        :param user_id: user ID
        :param multi_login: whether multi-device login is allowed
        :return:
        """
        return await self.update_model(db, user_id, {'is_multi_login': multi_login})

    async def delete(self, db: AsyncSession, user_id: int) -> int:
        """
        Delete user

        :param db: database session
        :param user_id: user ID
        :return:
        """
        user_role_stmt = delete(user_role).where(user_role.c.user_id == user_id)
        await db.execute(user_role_stmt)

        try:
            user_social = import_module_cached('backend.plugin.oauth2.crud.crud_user_social')
            user_social_dao = user_social.user_social_dao
        except (ImportError, AttributeError):
            pass
        else:
            await user_social_dao.delete_by_user_id(db, user_id)

        return await self.delete_model(db, user_id)

    async def get_join(
        self,
        db: AsyncSession,
        *,
        user_id: int | None = None,
        username: str | None = None,
    ) -> Any | None:
        """
        Get user relational info

        :param db: database session
        :param user_id: user ID
        :param username: username
        :return:
        """
        filters = {}

        if user_id:
            filters['id'] = user_id
        if username:
            filters['username'] = username

        result = await self.select_models(
            db,
            join_conditions=[
                JoinConfig(model=Dept, join_on=Dept.id == self.model.dept_id, fill_result=True),
                JoinConfig(model=user_role, join_on=user_role.c.user_id == self.model.id),
                JoinConfig(model=Role, join_on=Role.id == user_role.c.role_id, fill_result=True),
                JoinConfig(model=role_menu, join_on=role_menu.c.role_id == Role.id),
                JoinConfig(model=Menu, join_on=Menu.id == role_menu.c.menu_id, fill_result=True),
                JoinConfig(model=role_data_scope, join_on=role_data_scope.c.role_id == Role.id),
                JoinConfig(model=DataScope, join_on=DataScope.id == role_data_scope.c.data_scope_id, fill_result=True),
                JoinConfig(model=data_scope_rule, join_on=data_scope_rule.c.data_scope_id == DataScope.id),
                JoinConfig(model=DataRule, join_on=DataRule.id == data_scope_rule.c.data_rule_id, fill_result=True),
            ],
            **filters,
        )

        return select_join_serialize(
            result,
            relationships=[
                'User-m2o-Dept',
                'User-m2m-Role',
                'Role-m2m-Menu',
                'Role-m2m-DataScope:scopes',
                'DataScope-m2m-DataRule:rules',
            ],
        )


user_dao: CRUDUser = CRUDUser(User)
