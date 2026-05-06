from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ConversationSchemaBase(SchemaBase):
    """对话基础模型"""

    title: str | None = Field(None, description='对话标题')
    agent_id: int | None = Field(None, description='绑定 Agent ID')
    topology_id: int | None = Field(None, description='绑定拓扑 ID')
    source: str = Field(default='web', description='来源 web/api/arma')
    side: str | None = Field(None, description='阵营名 null/US/USSR/FIA (AI vs AI)')
    status: str = Field(default='active', description='状态 active/archived')


class CreateConversationParam(ConversationSchemaBase):
    """创建对话参数"""


class UpdateConversationParam(SchemaBase):
    """更新对话参数"""

    title: str | None = Field(None, description='对话标题')
    agent_id: int | None = Field(None, description='绑定 Agent ID')
    topology_id: int | None = Field(None, description='绑定拓扑 ID')
    mission_objective: dict | None = Field(None, description='任务目标 JSON')
    is_pinned: bool | None = Field(None, description='是否置顶')
    status: str | None = Field(None, description='状态 active/archived')


class GetConversationDetail(ConversationSchemaBase):
    """对话详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='ID')
    project_id: int = Field(description='项目 ID')
    user_id: int | None = Field(None, description='用户 ID')
    agent_id: int | None = Field(None, description='绑定 Agent ID')
    topology_id: int | None = Field(None, description='绑定拓扑 ID')
    side: str | None = Field(None, description='阵营名 null/US/USSR/FIA')
    conversation_group_id: int | None = Field(None, description='对话组 ID')
    mission_objective: dict | None = Field(None, description='任务目标 JSON')
    is_pinned: bool = Field(default=False, description='是否置顶')
    share_code: str | None = Field(None, description='分享码')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class ShareConversationResponse(SchemaBase):
    """分享对话响应"""

    share_code: str = Field(description='分享码')
    share_url: str = Field(description='分享链接')
