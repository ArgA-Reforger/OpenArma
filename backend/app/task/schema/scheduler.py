from datetime import datetime

from pydantic import ConfigDict, Field
from pydantic.types import JsonValue

from backend.app.task.enums import PeriodType, TaskSchedulerType
from backend.common.schema import SchemaBase


class TaskSchedulerSchemeBase(SchemaBase):
    """Task scheduler parameters"""

    name: str = Field(description='Task name')
    task: str = Field(description='Celery task to run')
    args: JsonValue | None = Field(default=None, description='Positional arguments the task accepts')
    kwargs: JsonValue | None = Field(default=None, description='Keyword arguments the task accepts')
    queue: str | None = Field(default=None, description='Queue defined in CELERY_TASK_QUEUES')
    exchange: str | None = Field(default=None, description='Exchange for low-level AMQP routing')
    routing_key: str | None = Field(default=None, description='Routing key for low-level AMQP routing')
    start_time: datetime | None = Field(default=None, description='Time the task starts triggering')
    expire_time: datetime | None = Field(default=None, description='Deadline after which the task no longer triggers')
    expire_seconds: int | None = Field(
        default=None, description='Number of seconds after which the task no longer triggers'
    )
    type: TaskSchedulerType = Field(description='Schedule type (0 interval, 1 crontab)')
    interval_every: int | None = Field(
        default=None, description='Number of interval periods before the task runs again'
    )
    interval_period: PeriodType | None = Field(default=None, description='Period type between task runs')
    crontab: str = Field(default='* * * * *', description='Crontab expression')
    one_off: bool = Field(default=False, description='Whether to run only once')
    remark: str | None = Field(default=None, description='Remark')


class CreateTaskSchedulerParam(TaskSchedulerSchemeBase):
    """Create task scheduler parameters"""


class UpdateTaskSchedulerParam(TaskSchedulerSchemeBase):
    """Update task scheduler parameters"""


class GetTaskSchedulerDetail(TaskSchedulerSchemeBase):
    """Task scheduler details"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Task scheduler ID')
    enabled: bool = Field(description='Whether the task is enabled')
    total_run_count: int = Field(description='Total number of runs so far')
    last_run_time: datetime | None = Field(None, description='Last run time')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
