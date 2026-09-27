from pydantic import Field

from backend.common.schema import SchemaBase


class UserPasswordHistoryBase(SchemaBase):
    """User password history base model"""

    user_id: int = Field(description='User ID')
    password: str = Field(description='Historical password')


class CreateUserPasswordHistoryParam(UserPasswordHistoryBase):
    """Create user password history record"""
