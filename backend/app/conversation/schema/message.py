from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class MessageSchemaBase(SchemaBase):
    """Message base model"""

    role: str = Field(description='Role user/assistant/system')
    content: str | None = Field(None, description='Content')
    structured_data: dict | None = Field(None, description='Structured data')
    metadata: dict | None = Field(None, validation_alias='metadata_', description='Message metadata')
    parent_message_id: int | None = Field(None, description='Parent message ID')


class GetMessageDetail(MessageSchemaBase):
    """Message details"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='ID')
    conversation_id: int = Field(description='Conversation ID')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')


class GetMessageWithBranches(GetMessageDetail):
    """Message details (including branch info)"""

    branch_count: int = Field(0, description='Number of AI reply branches')
    active_branch_index: int = Field(0, description='Currently active branch index (0-based)')


class UpdateMessageParam(SchemaBase):
    """Update message parameters"""

    content: str = Field(description='Message content')


class SendMessageParam(SchemaBase):
    """Send message parameters"""

    content: str = Field(description='Message content')


class SwitchBranchParam(SchemaBase):
    """Switch branch parameters"""

    target_branch_id: int = Field(description='Target branch message ID')
