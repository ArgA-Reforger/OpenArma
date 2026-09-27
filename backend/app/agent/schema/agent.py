from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class AgentSchemaBase(SchemaBase):
    name: str = Field(description='Agent name')
    description: str | None = Field(None, description='Description')
    system_prompt: str | None = Field(None, description='System prompt')
    rules: dict | list | None = Field(None, description='Rules')
    skills: dict | list | None = Field(None, description='Skills')
    llm_provider_id: int | None = Field(None, description='LLM provider ID')
    model_name: str | None = Field(None, description='Model name')
    temperature: float = Field(0.7, description='Temperature')
    top_p: float | None = Field(None, description='Top P')
    max_tokens: int | None = Field(None, description='Max token count')
    presence_penalty: float | None = Field(None, description='Presence penalty')
    frequency_penalty: float | None = Field(None, description='Frequency penalty')
    is_default: bool = Field(False, description='Whether user default agent')
    sort_order: int = Field(0, description='Sort order')
    visibility: str = Field('private', description='Visibility private/public/official')
    builtin_tools: dict | None = Field(None, description='Builtin tools configuration')
    enable_sub_agents: bool = Field(False, description='Allow dynamic sub-agent generation')


class CreateAgentParam(AgentSchemaBase):
    pass


class UpdateAgentParam(SchemaBase):
    name: str | None = Field(None, description='Agent name')
    description: str | None = Field(None, description='Description')
    system_prompt: str | None = Field(None, description='System prompt')
    rules: dict | list | None = Field(None, description='Rules')
    skills: dict | list | None = Field(None, description='Skills')
    llm_provider_id: int | None = Field(None, description='LLM provider ID')
    model_name: str | None = Field(None, description='Model name')
    temperature: float | None = Field(None, description='Temperature')
    top_p: float | None = Field(None, description='Top P')
    max_tokens: int | None = Field(None, description='Max token count')
    presence_penalty: float | None = Field(None, description='Presence penalty')
    frequency_penalty: float | None = Field(None, description='Frequency penalty')
    is_default: bool | None = Field(None, description='Whether user default agent')
    sort_order: int | None = Field(None, description='Sort order')
    visibility: str | None = Field(None, description='Visibility private/public/official')
    builtin_tools: dict | None = Field(None, description='Builtin tools configuration')
    enable_sub_agents: bool | None = Field(None, description='Allow dynamic sub-agent generation')


class GetAgentDetail(AgentSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Agent ID')
    user_id: int = Field(description='Owner ID')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
