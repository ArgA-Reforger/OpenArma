from collections.abc import Sequence

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model import Menu, role_menu
from backend.app.admin.schema.menu import CreateMenuParam, UpdateMenuParam


class CRUDMenu(CRUDPlus[Menu]):
    """Menu database operations"""

    async def get(self, db: AsyncSession, menu_id: int) -> Menu | None:
        """
        Get menu detail

        :param db: database session
        :param menu_id: menu ID
        :return:
        """
        return await self.select_model(db, menu_id)

    async def get_by_title(self, db: AsyncSession, title: str) -> Menu | None:
        """
        Get a menu by title

        :param db: database session
        :param title: menu title
        :return:
        """
        return await self.select_model_by_column(db, title=title, type__ne=2)

    async def get_all(self, db: AsyncSession, title: str | None, status: int | None) -> Sequence[Menu]:
        """
        Get menu list

        :param db: database session
        :param title: menu title
        :param status: menu status
        :return:
        """
        filters = {}

        if title is not None:
            filters['title__like'] = f'%{title}%'
        if status is not None:
            filters['status'] = status

        return await self.select_models_order(db, 'sort', 'asc', **filters)

    async def get_sidebar(self, db: AsyncSession, menu_ids: list[int] | None) -> Sequence[Menu]:
        """
        Get the user's menu sidebar

        :param db: database session
        :param menu_ids: menu ID list
        :return:
        """
        filters = {'type__in': [0, 1, 3, 4]}

        if menu_ids:
            filters['id__in'] = menu_ids

        return await self.select_models_order(db, 'sort', 'asc', **filters)

    async def create(self, db: AsyncSession, obj: CreateMenuParam) -> None:
        """
        Create menu

        :param db: database session
        :param obj: menu creation params
        :return:
        """
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, menu_id: int, obj: UpdateMenuParam) -> int:
        """
        Update menu

        :param db: database session
        :param menu_id: menu ID
        :param obj: menu update params
        :return:
        """
        return await self.update_model(db, menu_id, obj)

    async def delete(self, db: AsyncSession, menu_id: int) -> int:
        """
        Delete menu

        :param db: database session
        :param menu_id: menu ID
        :return:
        """
        role_menu_stmt = delete(role_menu).where(role_menu.c.menu_id == menu_id)
        await db.execute(role_menu_stmt)

        return await self.delete_model(db, menu_id)

    async def get_children(self, db: AsyncSession, menu_id: int) -> Sequence[Menu | None]:
        """
        Get sub-menu list

        :param db: database session
        :param menu_id: menu ID
        :return:
        """
        return await self.select_models(db, parent_id=menu_id)


menu_dao: CRUDMenu = CRUDMenu(Menu)
