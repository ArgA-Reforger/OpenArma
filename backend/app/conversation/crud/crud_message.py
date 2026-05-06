from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.conversation.model import Message
from backend.app.conversation.schema.message import UpdateMessageParam


class CRUDMessage(CRUDPlus[Message]):
    async def get(self, db: AsyncSession, pk: int) -> Message | None:
        return await self.select_model_by_column(db, id=pk, del_flag=False)

    async def get_list(self, conversation_id: int, *, after_id: int | None = None) -> Select:
        from sqlalchemy import select as sa_select
        stmt = (
            sa_select(self.model)
            .where(
                self.model.conversation_id == conversation_id,
                self.model.del_flag == False,  # noqa: E712
            )
        )
        if after_id is not None:
            stmt = stmt.where(self.model.id > after_id)
        return stmt.order_by(self.model.created_time.asc(), self.model.id.asc())

    async def update(self, db: AsyncSession, pk: int, obj: UpdateMessageParam) -> int:
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pk: int) -> int:
        return await self.delete_model_by_column(db, id=pk, logical_deletion=True, deleted_flag_column='del_flag')

    async def soft_delete_after(
        self, db: AsyncSession, conversation_id: int, after_message_id: int
    ) -> int:
        """Soft-delete all messages in a conversation created after the given message.
        Also backfill parent_message_id on assistant messages for branching."""
        from sqlalchemy import select as sa_select, update as sa_update

        ref_stmt = sa_select(self.model.created_time).where(self.model.id == after_message_id)
        ref_result = await db.execute(ref_stmt)
        ref_time = ref_result.scalar_one_or_none()
        if not ref_time:
            return 0

        backfill_stmt = (
            sa_update(self.model)
            .where(
                self.model.conversation_id == conversation_id,
                self.model.role == 'assistant',
                self.model.created_time > ref_time,
                self.model.del_flag == False,  # noqa: E712
                self.model.parent_message_id.is_(None),
            )
            .values(parent_message_id=after_message_id)
        )
        await db.execute(backfill_stmt)

        stmt = (
            sa_update(self.model)
            .where(
                self.model.conversation_id == conversation_id,
                self.model.created_time > ref_time,
                self.model.del_flag == False,  # noqa: E712
            )
            .values(del_flag=True)
        )
        result = await db.execute(stmt)
        return result.rowcount  # type: ignore

    async def soft_delete_last_assistant_replies(
        self, db: AsyncSession, conversation_id: int
    ) -> int:
        """Soft-delete all assistant messages after the last user message.
        Also backfill parent_message_id for branching support."""
        from sqlalchemy import select as sa_select, update as sa_update

        last_user_stmt = (
            sa_select(self.model.id, self.model.created_time)
            .where(
                self.model.conversation_id == conversation_id,
                self.model.role == 'user',
                self.model.del_flag == False,  # noqa: E712
            )
            .order_by(self.model.created_time.desc())
            .limit(1)
        )
        result = await db.execute(last_user_stmt)
        row = result.one_or_none()
        if not row:
            return 0

        last_user_id, last_user_time = row

        stmt = (
            sa_update(self.model)
            .where(
                self.model.conversation_id == conversation_id,
                self.model.role == 'assistant',
                self.model.created_time > last_user_time,
                self.model.del_flag == False,  # noqa: E712
            )
            .values(del_flag=True, parent_message_id=last_user_id)
        )
        result = await db.execute(stmt)
        return result.rowcount  # type: ignore

    async def get_last_user_message(
        self, db: AsyncSession, conversation_id: int
    ) -> Message | None:
        """Get the last non-deleted user message in a conversation."""
        from sqlalchemy import select as sa_select

        stmt = (
            sa_select(self.model)
            .where(
                self.model.conversation_id == conversation_id,
                self.model.role == 'user',
                self.model.del_flag == False,  # noqa: E712
            )
            .order_by(self.model.created_time.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_branches(
        self, db: AsyncSession, conversation_id: int, parent_message_id: int
    ) -> list[Message]:
        """
        Get all AI reply branches for a given user message,
        including soft-deleted ones, ordered by creation time.
        """
        from sqlalchemy import select as sa_select

        stmt = (
            sa_select(self.model)
            .where(
                self.model.conversation_id == conversation_id,
                self.model.parent_message_id == parent_message_id,
                self.model.role == 'assistant',
            )
            .order_by(self.model.created_time.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def switch_branch(
        self, db: AsyncSession, conversation_id: int,
        parent_message_id: int, target_message_id: int,
    ) -> int:
        """
        Activate a specific branch: set del_flag=False for the target message
        and del_flag=True for all other branches of the same parent.
        For multi-agent mode, branches are grouped by created_time proximity.
        """
        from sqlalchemy import select as sa_select, update as sa_update

        branches = await self.get_branches(db, conversation_id, parent_message_id)
        if not branches:
            return 0

        target = next((b for b in branches if b.id == target_message_id), None)
        if not target:
            return 0

        target_is_multi = target.metadata_ and target.metadata_.get('role') in ('agent', 'coordinator', 'aggregator')

        if target_is_multi:
            from datetime import timedelta
            target_time = target.created_time
            window = timedelta(seconds=5)

            same_group_ids = set()
            other_ids = set()
            for b in branches:
                if abs((b.created_time - target_time).total_seconds()) < window.total_seconds():
                    same_group_ids.add(b.id)
                else:
                    other_ids.add(b.id)

            if same_group_ids:
                stmt = (
                    sa_update(self.model)
                    .where(self.model.id.in_(same_group_ids))
                    .values(del_flag=False)
                )
                await db.execute(stmt)
            if other_ids:
                stmt = (
                    sa_update(self.model)
                    .where(self.model.id.in_(other_ids))
                    .values(del_flag=True)
                )
                await db.execute(stmt)
        else:
            branch_ids = [b.id for b in branches]
            if branch_ids:
                stmt = (
                    sa_update(self.model)
                    .where(self.model.id.in_(branch_ids))
                    .values(del_flag=True)
                )
                await db.execute(stmt)

            stmt = (
                sa_update(self.model)
                .where(self.model.id == target_message_id)
                .values(del_flag=False)
            )
            await db.execute(stmt)

        return 1

    async def get_branch_counts(
        self, db: AsyncSession, conversation_id: int
    ) -> dict[int, dict]:
        """
        For each user message that has multiple AI reply branches,
        return {parent_msg_id: {total: N, active_index: I}}.
        """
        from sqlalchemy import select as sa_select, func as sa_func

        stmt = (
            sa_select(
                self.model.parent_message_id,
                self.model.id,
                self.model.del_flag,
                self.model.created_time,
            )
            .where(
                self.model.conversation_id == conversation_id,
                self.model.role == 'assistant',
                self.model.parent_message_id.isnot(None),
            )
            .order_by(self.model.created_time.asc())
        )
        result = await db.execute(stmt)
        rows = result.all()

        groups: dict[int, list[tuple]] = {}
        for parent_id, msg_id, del_flag, created_time in rows:
            groups.setdefault(parent_id, []).append((msg_id, del_flag, created_time))

        branch_info: dict[int, dict] = {}
        for parent_id, msgs in groups.items():
            seen_times: list[float] = []
            branch_groups: list[list[tuple]] = []

            for msg_id, del_flag, ct in msgs:
                ts = ct.timestamp()
                matched = False
                for i, ref_ts in enumerate(seen_times):
                    if abs(ts - ref_ts) < 5:
                        branch_groups[i].append((msg_id, del_flag))
                        matched = True
                        break
                if not matched:
                    seen_times.append(ts)
                    branch_groups.append([(msg_id, del_flag)])

            if len(branch_groups) <= 1:
                continue

            active_idx = 0
            for i, group in enumerate(branch_groups):
                if any(not df for _, df in group):
                    active_idx = i
                    break

            branch_info[parent_id] = {
                'total': len(branch_groups),
                'active_index': active_idx,
            }

        return branch_info

    async def get_recent(
        self, db: AsyncSession, conversation_id: int, limit: int = 20
    ) -> list[Message]:
        from sqlalchemy import select as sa_select

        stmt = (
            sa_select(self.model)
            .where(
                self.model.conversation_id == conversation_id,
                self.model.del_flag == False,  # noqa: E712
            )
            .order_by(self.model.created_time.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    async def count_messages(
        self, db: AsyncSession, conversation_id: int
    ) -> int:
        from sqlalchemy import func as sa_func, select as sa_select

        stmt = (
            sa_select(sa_func.count())
            .select_from(self.model)
            .where(
                self.model.conversation_id == conversation_id,
                self.model.del_flag == False,  # noqa: E712
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one()


message_dao: CRUDMessage = CRUDMessage(Message)
