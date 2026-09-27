from datetime import datetime

from pydantic import ConfigDict, Field, field_validator

from backend.common.exception import errors
from backend.common.schema import SchemaBase
from backend.utils.pattern_validate import is_english_identifier


class GenBusinessSchemaBase(SchemaBase):
    """Code generator business base model"""

    app_name: str = Field(description='App name (English)')
    table_name: str = Field(description='Table name (English)')
    doc_comment: str = Field(description='Doc comment (used for function/parameter docs)')
    table_comment: str | None = Field(None, description='Table description')
    class_name: str | None = Field(None, description='Base class name for the generated Python code')
    schema_name: str | None = Field(None, description='Base class name for the generated Python Schema code')
    filename: str | None = Field(None, description='Base filename for the generated Python code')
    datetime_mixin: bool = Field(True, description='Whether to include time mixin columns')
    api_version: str = Field('v1', description='API version')
    tag: str | None = Field(None, description='API tag (used for route grouping)')
    gen_path: str | None = Field(None, description='Generation path (defaults to the backend/app directory)')
    remark: str | None = Field(None, description='Remark')

    @field_validator('app_name', 'table_name')
    @classmethod
    def validate_english_only(cls, v: str) -> str:
        """Validate that the field contains only English characters"""
        if not is_english_identifier(v):
            raise errors.RequestError(msg='Must start with an English letter and contain only English letters and underscores')
        return v


class CreateGenBusinessParam(GenBusinessSchemaBase):
    """Create code generator business parameters"""


class UpdateGenBusinessParam(GenBusinessSchemaBase):
    """Update code generator business parameters"""


class GetGenBusinessDetail(GenBusinessSchemaBase):
    """Get code generator business detail"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Primary key ID')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
