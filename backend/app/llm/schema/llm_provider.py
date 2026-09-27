from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ModelEntry(SchemaBase):
    """Model entry, including verification status"""

    name: str = Field(description='Model name')
    verified_at: str | None = Field(None, description='Last verification time (ISO string)')
    verified_ok: bool | None = Field(None, description='Whether verification passed')


def normalize_models(raw: list | None) -> list[dict] | None:
    """Compatibility for legacy format: convert ["str"] to [{"name": "str", ...}]"""
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
    """Base LLM provider model"""

    name: str = Field(description='Provider name')
    provider_type: str = Field(description='Provider type')
    api_base: str | None = Field(None, description='API base URL')
    models: list[ModelEntry] | None = Field(None, description='Available model list')
    rpm_limit: int | None = Field(None, ge=1, description='RPM limit (null = unlimited)')
    tpm_limit: int | None = Field(None, ge=1, description='TPM limit (null = unlimited)')
    is_active: bool = Field(default=True, description='Whether enabled')
    visibility: str = Field(default='private', description='Visibility private/public/official')


class CreateLLMProviderParam(LLMProviderSchemaBase):
    """Create LLM provider parameters"""

    api_key: str | None = Field(None, description='API key (plaintext, encrypted when stored)')


class UpdateLLMProviderParam(SchemaBase):
    """Update LLM provider parameters"""

    name: str | None = Field(None, description='Provider name')
    provider_type: str | None = Field(None, description='Provider type')
    api_base: str | None = Field(None, description='API base URL')
    api_key: str | None = Field(None, description='API key (plaintext, re-encrypted if provided on update)')
    models: list[ModelEntry] | None = Field(None, description='Available model list')
    rpm_limit: int | None = Field(None, ge=1, description='RPM limit (null = unlimited)')
    tpm_limit: int | None = Field(None, ge=1, description='TPM limit (null = unlimited)')
    is_active: bool | None = Field(None, description='Whether enabled')
    visibility: str | None = Field(None, description='Visibility private/public/official')


class VerifyModelParam(SchemaBase):
    """Verify model connection parameters"""

    model_name: str = Field(description='Model name to verify')


class GetLLMProviderDetail(LLMProviderSchemaBase):
    """LLM provider details"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Primary key ID')
    user_id: int = Field(description='User ID')
    api_key_masked: str | None = Field(None, description='Masked API key')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
