from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ModelEntry(SchemaBase):
    """模型条目，包含验证状态"""

    name: str = Field(description='模型名称')
    verified_at: str | None = Field(None, description='最后验证时间 (ISO 字符串)')
    verified_ok: bool | None = Field(None, description='验证是否通过')


def normalize_models(raw: list | None) -> list[dict] | None:
    """兼容旧格式：将 ["str"] 转为 [{"name": "str", ...}]"""
    if not raw:
        return raw
    result = []
    for item in raw:
        if isinstance(item, str):
            result.append({'name': item, 'verified_at': None, 'verified_ok': None})
        elif isinstance(item, dict):
            result.append(item)
        else:
            result.append({'name': str(item), 'verified_at': None, 'verified_ok': None})
    return result


class LLMProviderSchemaBase(SchemaBase):
    """LLM 服务商基础模型"""

    name: str = Field(description='服务商名称')
    provider_type: str = Field(description='服务商类型')
    api_base: str | None = Field(None, description='API 基础地址')
    models: list[ModelEntry] | None = Field(None, description='可用模型列表')
    rpm_limit: int | None = Field(None, ge=1, description='每分钟请求数上限（null=不限制）')
    tpm_limit: int | None = Field(None, ge=1, description='每分钟 Token 数上限（null=不限制）')
    is_active: bool = Field(default=True, description='是否启用')
    visibility: str = Field(default='private', description='可见性 private/public/official')


class CreateLLMProviderParam(LLMProviderSchemaBase):
    """创建 LLM 服务商参数"""

    api_key: str | None = Field(None, description='API Key（明文，存储时加密）')


class UpdateLLMProviderParam(SchemaBase):
    """更新 LLM 服务商参数"""

    name: str | None = Field(None, description='服务商名称')
    provider_type: str | None = Field(None, description='服务商类型')
    api_base: str | None = Field(None, description='API 基础地址')
    api_key: str | None = Field(None, description='API Key（明文，仅更新时提供则重新加密）')
    models: list[ModelEntry] | None = Field(None, description='可用模型列表')
    rpm_limit: int | None = Field(None, ge=1, description='每分钟请求数上限（null=不限制）')
    tpm_limit: int | None = Field(None, ge=1, description='每分钟 Token 数上限（null=不限制）')
    is_active: bool | None = Field(None, description='是否启用')
    visibility: str | None = Field(None, description='可见性 private/public/official')


class VerifyModelParam(SchemaBase):
    """验证模型连接参数"""

    model_name: str = Field(description='要验证的模型名称')


class GetLLMProviderDetail(LLMProviderSchemaBase):
    """LLM 服务商详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='主键 ID')
    user_id: int = Field(description='用户 ID')
    api_key_masked: str | None = Field(None, description='API Key 脱敏显示')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
