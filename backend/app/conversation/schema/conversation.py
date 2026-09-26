from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ConversationSchemaBase(SchemaBase):
    """Conversation base model"""

    title: str | None = Field(None, description='Conversation title')
    agent_id: int | None = Field(None, description='Bound Agent ID')
    topology_id: int | None = Field(None, description='Bound topology ID')
    source: str = Field(default='web', description='Source web/api/arma')
    side: str | None = Field(None, description='Faction name null/US/USSR/FIA (AI vs AI)')
    status: str = Field(default='active', description='Status active/archived')


class CreateConversationParam(ConversationSchemaBase):
    """Create conversation parameters"""


class UpdateConversationParam(SchemaBase):
    """Update conversation parameters"""

    title: str | None = Field(None, description='Conversation title')
    agent_id: int | None = Field(None, description='Bound Agent ID')
    topology_id: int | None = Field(None, description='Bound topology ID')
    mission_objective: dict | None = Field(None, description='Mission objective JSON')
    is_pinned: bool | None = Field(None, description='Whether it is pinned')
    status: str | None = Field(None, description='Status active/archived')


class GetConversationDetail(ConversationSchemaBase):
    """Conversation details"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='ID')
    project_id: int = Field(description='Project ID')
    user_id: int | None = Field(None, description='User ID')
    agent_id: int | None = Field(None, description='Bound Agent ID')
    topology_id: int | None = Field(None, description='Bound topology ID')
    side: str | None = Field(None, description='Faction name null/US/USSR/FIA')
    conversation_group_id: int | None = Field(None, description='Conversation group ID')
    mission_objective: dict | None = Field(None, description='Mission objective JSON')
    is_pinned: bool = Field(default=False, description='Whether it is pinned')
    share_code: str | None = Field(None, description='Share code')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')


class ShareConversationResponse(SchemaBase):
    """Share conversation response"""

    share_code: str = Field(description='Share code')
    share_url: str = Field(description='Share link')
