from __future__ import annotations

import asyncio
import json
import math

from datetime import datetime, timedelta
from multiprocessing.util import Finalize
from typing import TYPE_CHECKING

from celery import current_app, schedules
from celery.beat import ScheduleEntry, Scheduler
from celery.signals import beat_init
from celery.utils.log import get_logger
from sqlalchemy import select
from sqlalchemy.exc import DatabaseError, InterfaceError

from backend.app.task.enums import PeriodType, TaskSchedulerType
from backend.app.task.model.scheduler import TaskScheduler
from backend.app.task.schema.scheduler import CreateTaskSchedulerParam
from backend.app.task.utils.tzcrontab import TzAwareCrontab, crontab_verify
from backend.common.exception import errors
from backend.core.conf import settings
from backend.database.db import async_db_session
from backend.database.redis import redis_client
from backend.utils.async_helper import run_await
from backend.utils.serializers import select_as_dict
from backend.utils.timezone import timezone

if TYPE_CHECKING:
    from redis.asyncio.lock import Lock

# This scheduler must wake up more often than the usual 5 minutes, because it needs to
# account for external changes to the schedule
DEFAULT_MAX_INTERVAL = 5  # seconds

# Schedule lock duration, to avoid duplicate creation
DEFAULT_MAX_LOCK_TIMEOUT = DEFAULT_MAX_INTERVAL * 5  # seconds

logger = get_logger('fba.schedulers')


class ModelEntry(ScheduleEntry):
    """Task schedule entity"""

    def __init__(self, model: TaskScheduler, app=None) -> None:  # noqa:ANN001,C901
        super().__init__(
            app=app or current_app._get_current_object(),
            name=model.name,
            task=model.task,
        )
        try:
            if (
                model.type == TaskSchedulerType.INTERVAL
                and model.interval_every is not None
                and model.interval_period is not None
            ):
                self.schedule = schedules.schedule(timedelta(**{model.interval_period: model.interval_every}))
            elif model.type == TaskSchedulerType.CRONTAB and model.crontab is not None:
                self.schedule = TzAwareCrontab.from_string(model.crontab)
            else:
                raise errors.NotFoundError(msg=f'{self.name} has an empty schedule!')
            # logger.debug('Schedule: {}'.format(self.schedule))
        except Exception as e:
            logger.error(f'Disabling task {self.name} with an empty schedule, details: {e}')
            asyncio.create_task(self._disable(model))

        try:
            self.args = json.loads(model.args) if model.args else None
            self.kwargs = json.loads(model.kwargs) if model.kwargs else None
        except ValueError as exc:
            logger.error(f'Disabling task with invalid arguments: {self.name}; error: {exc!s}')
            asyncio.create_task(self._disable(model))

        self.options = {}
        for option in ['queue', 'exchange', 'routing_key']:
            value = getattr(model, option)
            if value is None:
                continue
            self.options[option] = value

        if model.expire_seconds is not None:
            self.options['expires'] = model.expire_seconds
        elif model.expire_time is not None:
            self.options['expires'] = timezone.from_datetime(model.expire_time)

        if not model.last_run_time:
            model.last_run_time = timezone.now()
            if model.start_time:
                model.last_run_time = timezone.from_datetime(model.start_time) - timedelta(days=365)

        self.last_run_at = timezone.from_datetime(model.last_run_time)
        self.options['periodic_task_name'] = model.name
        self.model = model

    async def _disable(self, model: TaskScheduler) -> None:
        """Disable the task"""
        model.no_changes = True
        self.model.enabled = self.enabled = model.enabled = False
        async with async_db_session.begin() as db:
            stmt = select(TaskScheduler).where(TaskScheduler.id == model.id)
            query = await db.execute(stmt)
            task = query.scalars().first()
            if task:
                task.no_changes = True
                task.enabled = False

    def is_due(self) -> tuple[bool, int | float | datetime]:
        """Task due status"""
        if not self.model.enabled:
            # Delay 5 seconds when re-enabling
            return schedules.schedstate(is_due=False, next=5)

        # Only run after 'start_time'
        if self.model.start_time is not None:
            now = timezone.now()
            start_time = timezone.from_datetime(self.model.start_time)
            if now < start_time:
                delay = math.ceil((start_time - now).total_seconds())
                return schedules.schedstate(is_due=False, next=delay)

        # One-off task
        if self.model.one_off and self.model.enabled and self.model.total_run_count > 0:
            self.model.enabled = False
            self.model.total_run_count = 0
            self.model.no_changes = False
            save_fields = ('enabled',)
            run_await(self.save)(save_fields)
            return schedules.schedstate(is_due=False, next=1000000000)  # High delay, to avoid rechecking

        return self.schedule.is_due(self.last_run_at)

    def __next__(self):  # noqa: ANN204
        self.model.last_run_time = timezone.now()
        self.model.total_run_count += 1
        self.model.no_changes = True
        return self.__class__(self.model)

    next = __next__

    async def save(self, fields: tuple = ()) -> None:
        """
        Save task state fields

        :param fields: other fields to save
        :return:
        """
        async with async_db_session.begin() as db:
            stmt = select(TaskScheduler).where(TaskScheduler.id == self.model.id).with_for_update()
            query = await db.execute(stmt)
            task = query.scalars().first()
            if task:
                for field in ['last_run_time', 'total_run_count', 'no_changes']:
                    setattr(task, field, getattr(self.model, field))
                for field in fields:
                    setattr(task, field, getattr(self.model, field))
            else:
                logger.warning(f'Task {self.model.name} does not exist, skipping update')

    @classmethod
    async def from_entry(cls, name, app=None, **entry) -> ModelEntry:  # noqa: ANN001
        """Save or update the local task schedule"""
        async with async_db_session.begin() as db:
            stmt = select(TaskScheduler).where(TaskScheduler.name == name)
            query = await db.execute(stmt)
            task = query.scalars().first()
            temp = await cls._unpack_fields(name, **entry)
            if not task:
                task = TaskScheduler(**temp)
                db.add(task)
            else:
                for key, value in temp.items():
                    setattr(task, key, value)
            res = cls(task, app=app)
            return res

    @staticmethod
    async def to_model_schedule(name: str, task: str, schedule: schedules.schedule | TzAwareCrontab) -> TaskScheduler:
        schedule = schedules.maybe_schedule(schedule)

        async with async_db_session() as db:
            if isinstance(schedule, schedules.schedule):
                every = max(schedule.run_every.total_seconds(), 0)
                spec = {
                    'name': name,
                    'type': TaskSchedulerType.INTERVAL.value,
                    'interval_every': every,
                    'interval_period': PeriodType.SECONDS.value,
                }
                stmt = select(TaskScheduler).filter_by(**spec)
                query = await db.execute(stmt)
                obj = query.scalars().first()
                if not obj:
                    obj = TaskScheduler(**CreateTaskSchedulerParam(task=task, **spec).model_dump())
            elif isinstance(schedule, schedules.crontab):
                crontab = f'{schedule._orig_minute} {schedule._orig_hour} {schedule._orig_day_of_month} {schedule._orig_month_of_year} {schedule._orig_day_of_week}'  # noqa: E501
                crontab_verify(crontab)
                spec = {
                    'name': name,
                    'type': TaskSchedulerType.CRONTAB.value,
                    'crontab': crontab,
                }
                stmt = select(TaskScheduler).filter_by(**spec)
                query = await db.execute(stmt)
                obj = query.scalars().first()
                if not obj:
                    obj = TaskScheduler(**CreateTaskSchedulerParam(task=task, **spec).model_dump())
            else:
                raise errors.NotFoundError(msg=f'Unsupported schedule type: {schedule}')

            return obj

    @classmethod
    async def _unpack_fields(
        cls,
        name: str,
        task: str,
        schedule: schedules.schedule | TzAwareCrontab,
        args: tuple | None = None,
        kwargs: dict | None = None,
        options: dict | None = None,
        **entry,
    ) -> dict:
        model_schedule = await cls.to_model_schedule(name, task, schedule)
        model_dict = select_as_dict(model_schedule)
        for k in ['id', 'created_time', 'updated_time']:
            try:
                del model_dict[k]
            except KeyError:  # noqa:PERF203
                continue
        model_dict.update(
            args=json.dumps(args, ensure_ascii=False) if args else None,
            kwargs=json.dumps(kwargs, ensure_ascii=False) if kwargs else None,
            **cls._unpack_options(**options or {}),
            **entry,
        )
        return model_dict

    @classmethod
    def _unpack_options(
        cls,
        queue: str | None = None,
        exchange: str | None = None,
        routing_key: str | None = None,
        start_time: datetime | None = None,
        expires: datetime | None = None,
        expire_seconds: int | None = None,
        *,
        one_off: bool = False,
    ) -> dict:
        data = {
            'queue': queue,
            'exchange': exchange,
            'routing_key': routing_key,
            'start_time': start_time,
            'expire_time': None,
            'expire_seconds': expire_seconds,
            'one_off': one_off,
        }
        if expires:
            if isinstance(expires, int):
                data['expire_seconds'] = expires
            elif isinstance(expires, timedelta):
                data['expire_time'] = timezone.now() + expires
            elif isinstance(expires, datetime):
                data['expire_time'] = expires
        return data


class DatabaseScheduler(Scheduler):
    """Database scheduler"""

    Entry = ModelEntry

    _schedule = None
    _last_update = None
    _initial_read = True
    _heap_invalidated = False

    lock: Lock | None = None
    lock_key = f'{settings.CELERY_REDIS_PREFIX}:beat_lock'

    def __init__(self, *args, **kwargs) -> None:
        self.app = kwargs['app']
        self._dirty = set()
        super().__init__(*args, **kwargs)
        self._finalize = Finalize(self, self.sync, exitpriority=5)
        self.max_interval = kwargs.get('max_interval') or self.app.conf.beat_max_loop_interval or DEFAULT_MAX_INTERVAL

    def schedules_equal(self, *args, **kwargs) -> bool:
        """Override the parent function"""
        if self._heap_invalidated:
            self._heap_invalidated = False
            return False
        return super().schedules_equal(*args, **kwargs)

    def reserve(self, entry):  # noqa: ANN001, ANN201
        """Override the parent function"""
        new_entry = next(entry)
        # Entries need to be stored by name, because entries may change
        self._dirty.add(new_entry.name)
        return new_entry

    def setup_schedule(self) -> None:
        """Override the parent function"""
        logger.info('setup_schedule')
        tasks = self.schedule
        self.install_default_entries(tasks)
        self.update_from_dict(self.app.conf.beat_schedule)

    def sync(self) -> None:
        """Override the parent function"""
        tried = set()
        failed = set()
        try:
            while self._dirty:
                name = self._dirty.pop()
                try:
                    tasks = self.schedule
                    run_await(tasks[name].save)()
                    logger.debug(f'Saved the latest state of task {name} to the database')
                    tried.add(name)
                except KeyError as e:
                    logger.error(f'Failed to save the latest state of task {name}: {e} ')
                    failed.add(name)
        except DatabaseError:
            logger.exception('Database error occurred while syncing')
        except InterfaceError as e:
            logger.warning(f'DatabaseScheduler InterfaceError: {e!s}, waiting to retry on the next call...')
        finally:
            # Retry later (only for the failed ones)
            self._dirty |= failed

    def tick(self, **kwargs) -> float:
        """Override the parent function"""
        if self.lock:
            logger.debug('beat: Extending lock...')
            run_await(self.lock.extend)(DEFAULT_MAX_LOCK_TIMEOUT, replace_ttl=True)

        return super().tick(**kwargs)

    def close(self) -> None:
        """Override the parent function"""
        if self.lock:
            logger.info('beat: Releasing lock')
            if run_await(self.lock.owned)():
                run_await(self.lock.release)()
            self.lock = None

        super().close()

    def update_from_dict(self, beat_dict: dict) -> None:
        """Override the parent function"""
        s = {}
        name = None
        try:
            for name, entry_fields in beat_dict.items():
                entry = run_await(self.Entry.from_entry)(name, app=self.app, **entry_fields)
                if entry.model.enabled:
                    s[name] = entry
        except Exception:
            logger.error(f'Failed to add task {name} to the database')
            raise

        tasks = self.schedule
        tasks.update(s)

    def schedule_changed(self) -> bool | None:
        """Task schedule change status"""
        now = timezone.now()
        last_update = run_await(redis_client.get)(f'{settings.CELERY_REDIS_PREFIX}:last_update')
        if not last_update:
            run_await(redis_client.set)(f'{settings.CELERY_REDIS_PREFIX}:last_update', timezone.to_str(now))
            return False

        last, ts = self._last_update, timezone.from_str(last_update)
        try:
            if ts and ts > (last or ts):
                return True
        finally:
            self._last_update = now

    async def get_all_task_schedulers(self) -> dict:
        """Get all task schedules"""
        async with async_db_session() as db:
            logger.debug('DatabaseScheduler: Fetching database schedule')
            stmt = select(TaskScheduler).where(TaskScheduler.enabled == True)  # noqa: E712
            query = await db.execute(stmt)
            schedulers = query.scalars().all()
            s = {}
            for scheduler in schedulers:
                s[scheduler.name] = self.Entry(scheduler, app=self.app)
            return s

    @property
    def schedule(self) -> dict[str, ModelEntry]:
        """Get the task schedule"""
        initial = update = False
        if self._initial_read:
            logger.debug('DatabaseScheduler: initial read')
            initial = update = True
            self._initial_read = False
        elif self.schedule_changed():
            logger.info('DatabaseScheduler: Schedule changed.')
            update = True

        if update:
            logger.debug('beat: Synchronizing schedule...')
            self.sync()
            self._schedule = run_await(self.get_all_task_schedulers)()
            # Schedule has changed, invalidate the heap in Scheduler.tick
            if not initial:
                self._heap = []
                self._heap_invalidated = True
            logger.debug(
                'Current schedule:\n%s',
                '\n'.join(repr(entry) for entry in self._schedule.values()),
            )

        # logger.debug(self._schedule)
        return self._schedule


@beat_init.connect
def acquire_distributed_beat_lock(sender=None, **kwargs) -> None:  # noqa: ANN001
    """
    Try to acquire the lock on startup

    :param sender: the sender the receiver should respond to
    :return:
    """
    scheduler = sender.scheduler
    if not scheduler.lock_key:
        return

    logger.debug('beat: Acquiring lock...')
    lock = redis_client.lock(
        scheduler.lock_key,
        timeout=DEFAULT_MAX_LOCK_TIMEOUT,
        sleep=scheduler.max_interval,
    )

    run_await(lock.acquire)()
    logger.info('beat: Acquired lock')
    scheduler.lock = lock
