from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class MessageSchemaBase(SchemaBase):
    """消息基础模型"""

    role: str = Field(description='角色 user/assistant/system')
    content: str | None = Field(None, description='内容')
    structured_data: dict | None = Field(None, description='结构化数据')
    metadata: dict | None = Field(None, validation_alias='metadata_', description='消息元数据')
    parent_message_id: int | None = Field(None, description='父消息 ID')


class GetMessageDetail(MessageSchemaBase):
    """消息详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='ID')
    conversation_id: int = Field(description='对话 ID')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class GetMessageWithBranches(GetMessageDetail):
    """消息详情（含分支信息）"""

    branch_count: int = Field(0, description='AI 回复分支数')
    active_branch_index: int = Field(0, description='当前活跃分支索引（0-based）')


class UpdateMessageParam(SchemaBase):
    """更新消息参数"""

    content: str = Field(description='消息内容')


class SendMessageParam(SchemaBase):
    """发送消息参数"""

    content: str = Field(description='消息内容')


class SwitchBranchParam(SchemaBase):
    """切换分支参数"""

    target_branch_id: int = Field(description='目标分支消息 ID')
