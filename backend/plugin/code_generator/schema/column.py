from pydantic import ConfigDict, Field, field_validator

from backend.common.schema import SchemaBase
from backend.plugin.code_generator.utils.type_conversion import sql_type_to_sqlalchemy


class GenColumnSchemaBase(SchemaBase):
    """Code generator model base model"""

    name: str = Field(description='Column name')
    comment: str | None = Field(None, description='Column description')
    type: str = Field(description='SQLA model column type')
    default: str | None = Field(None, description='Column default value')
    sort: int = Field(description='Column sort order')
    length: int = Field(description='Column length')
    is_pk: bool = Field(False, description='Whether it is a primary key')
    is_nullable: bool = Field(False, description='Whether it can be null')
    gen_business_id: int = Field(description='Code generator business ID')

    @field_validator('type')
    @classmethod
    def normalize_type(cls, v: str) -> str:
        """Normalize the type"""
        return sql_type_to_sqlalchemy(v)


class CreateGenColumnParam(GenColumnSchemaBase):
    """Create code generator model column parameters"""


class UpdateGenColumnParam(GenColumnSchemaBase):
    """Update code generator model column parameters"""


class GetGenColumnDetail(GenColumnSchemaBase):
    """Get code generator model column detail"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Primary key ID')
    pd_type: str = Field(description='Pydantic type for the column type')
