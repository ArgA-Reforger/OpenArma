from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.enums import StatusType
from backend.common.schema import SchemaBase
from backend.plugin.notice.enums import NoticeType


class NoticeSchemaBase(SchemaBase):
    """Notice base model"""

    title: str = Field(description='Title')
    type: NoticeType = Field(description='Type (0: notice, 1: announcement)')
    status: StatusType = Field(description='Status (0: hidden, 1: shown)')
    content: str = Field(description='Content')


class CreateNoticeParam(NoticeSchemaBase):
    """Create notice parameters"""


class UpdateNoticeParam(NoticeSchemaBase):
    """Update notice parameters"""


class DeleteNoticeParam(SchemaBase):
    """Delete notice parameters"""

    pks: list[int] = Field(description='List of notice IDs')


class GetNoticeDetail(NoticeSchemaBase):
    """Notice detail"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Notice ID')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
