from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.enums import RoleDataRuleExpressionType, RoleDataRuleOperatorType
from backend.common.schema import SchemaBase


class DataRuleSchemaBase(SchemaBase):
    """Data rule base model"""

    name: str = Field(description='Rule name')
    model: str = Field(description='Model name')
    column: str = Field(description='Field name')
    operator: RoleDataRuleOperatorType = Field(description='Operator (AND/OR)')
    expression: RoleDataRuleExpressionType = Field(description='Expression type')
    value: str = Field(description='Rule value')


class CreateDataRuleParam(DataRuleSchemaBase):
    """Data rule creation params"""


class UpdateDataRuleParam(DataRuleSchemaBase):
    """Data rule update params"""


class DeleteDataRuleParam(SchemaBase):
    """Data rule deletion params"""

    pks: list[int] = Field(description='Rule ID list')


class GetDataRuleDetail(DataRuleSchemaBase):
    """Data rule detail"""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: int = Field(description='Rule ID')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')


class GetDataRuleColumnDetail(SchemaBase):
    """Field detail of a model available for data rules"""

    key: str = Field(description='Field name')
    comment: str | None = Field(description='Field comment')


class GetDataRuleTemplateVariableDetail(SchemaBase):
    """Template variable detail available for data rules"""

    key: str = Field(description='Variable identifier')
    comment: str = Field(description='Variable description')
