import asyncio

from datetime import datetime

import sqlalchemy as sa

from sqlalchemy import event
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.exception import errors
from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.core.conf import settings
from backend.database.redis import redis_client
from backend.utils.timezone import timezone


class TaskScheduler(Base):
    """Task scheduler table"""

    __tablename__ = 'task_scheduler'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(64), unique=True, comment='Task name')
    task: Mapped[str] = mapped_column(sa.String(256), comment='Celery task to run')
    args: Mapped[str | None] = mapped_column(sa.JSON(), comment='Positional arguments the task accepts')
    kwargs: Mapped[str | None] = mapped_column(sa.JSON(), comment='Keyword arguments the task accepts')
    queue: Mapped[str | None] = mapped_column(sa.String(256), comment='Queue defined in CELERY_TASK_QUEUES')
    exchange: Mapped[str | None] = mapped_column(sa.String(256), comment='Exchange for low-level AMQP routing')
    routing_key: Mapped[str | None] = mapped_column(sa.String(256), comment='Routing key for low-level AMQP routing')
    start_time: Mapped[datetime | None] = mapped_column(TimeZone, comment='Time the task starts triggering')
    expire_time: Mapped[datetime | None] = mapped_column(
        TimeZone, comment='Deadline after which the task no longer triggers'
    )
    expire_seconds: Mapped[int | None] = mapped_column(
        comment='Number of seconds after which the task no longer triggers'
    )
    type: Mapped[int] = mapped_column(comment='Schedule type (0 interval, 1 crontab)')
    interval_every: Mapped[int | None] = mapped_column(comment='Number of interval periods before the task runs again')
    interval_period: Mapped[str | None] = mapped_column(sa.String(256), comment='Period type between task runs')
    crontab: Mapped[str | None] = mapped_column(sa.String(64), default='* * * * *', comment='Crontab expression')
    one_off: Mapped[bool] = mapped_column(default=False, comment='Whether to run only once')
    enabled: Mapped[bool] = mapped_column(default=True, comment='Whether the task is enabled')
    total_run_count: Mapped[int] = mapped_column(default=0, comment='Total number of times the task has triggered')
    last_run_time: Mapped[datetime | None] = mapped_column(
        TimeZone, default=None, comment='Time the task last triggered'
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='Remark')

    no_changes: bool = False

    @staticmethod
    def before_insert_or_update(mapper, connection, target) -> None:  # noqa: ANN001
        if target.expire_seconds is not None and target.expire_time:
            raise errors.ConflictError(msg='Only one of expires and expire_seconds can be set')

    @classmethod
    def changed(cls, mapper, connection, target) -> None:  # noqa: ANN001
        if not target.no_changes:
            cls.update_changed(mapper, connection, target)

    @classmethod
    async def update_changed_async(cls) -> None:
        now = timezone.now()
        await redis_client.set(f'{settings.CELERY_REDIS_PREFIX}:last_update', timezone.to_str(now))

    @classmethod
    def update_changed(cls, mapper, connection, target) -> None:  # noqa: ANN001
        asyncio.create_task(cls.update_changed_async())


# Event listeners
event.listen(TaskScheduler, 'before_insert', TaskScheduler.before_insert_or_update)
event.listen(TaskScheduler, 'before_update', TaskScheduler.before_insert_or_update)
event.listen(TaskScheduler, 'after_insert', TaskScheduler.update_changed)
event.listen(TaskScheduler, 'after_delete', TaskScheduler.update_changed)
event.listen(TaskScheduler, 'after_update', TaskScheduler.changed)
