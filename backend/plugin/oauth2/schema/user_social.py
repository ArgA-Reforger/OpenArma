from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase
from backend.plugin.oauth2.enums import UserSocialType


class UserSocialSchemaBase(SchemaBase):
    """User social base model"""

    sid: str = Field(description='Third-party user ID')
    source: UserSocialType = Field(description='Social platform')


class CreateUserSocialParam(UserSocialSchemaBase):
    """Create user social parameters"""

    user_id: int = Field(description='User ID')


class UpdateUserSocialParam(SchemaBase):
    """Update user social parameters"""


class GetUserSocialDetail(CreateUserSocialParam):
    """Get user social detail"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='User social ID')
