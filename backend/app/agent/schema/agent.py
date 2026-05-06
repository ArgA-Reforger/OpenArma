from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class AgentSchemaBase(SchemaBase):
    name: str = Field(description='Agent 名称')
    description: str | None = Field(None, description='描述')
    system_prompt: str | None = Field(None, description='系统提示词')
    rules: dict | list | None = Field(None, description='规则')
    skills: dict | list | None = Field(None, description='技能')
    llm_provider_id: int | None = Field(None, description='LLM 提供商 ID')
    model_name: str | None = Field(None, description='模型名称')
    temperature: float = Field(0.7, description='温度')
    top_p: float | None = Field(None, description='Top P')
    max_tokens: int | None = Field(None, description='最大 token 数')
    presence_penalty: float | None = Field(None, description='存在惩罚')
    frequency_penalty: float | None = Field(None, description='频率惩罚')
    is_default: bool = Field(False, description='是否为用户默认 Agent')
    sort_order: int = Field(0, description='排序')
    visibility: str = Field('private', description='可见性 private/public/official')
    builtin_tools: dict | None = Field(None, description='内置工具配置')
    enable_sub_agents: bool = Field(False, description='允许动态生成子代理')


class CreateAgentParam(AgentSchemaBase):
    pass


class UpdateAgentParam(SchemaBase):
    name: str | None = Field(None, description='Agent 名称')
    description: str | None = Field(None, description='描述')
    system_prompt: str | None = Field(None, description='系统提示词')
    rules: dict | list | None = Field(None, description='规则')
    skills: dict | list | None = Field(None, description='技能')
    llm_provider_id: int | None = Field(None, description='LLM 提供商 ID')
    model_name: str | None = Field(None, description='模型名称')
    temperature: float | None = Field(None, description='温度')
    top_p: float | None = Field(None, description='Top P')
    max_tokens: int | None = Field(None, description='最大 token 数')
    presence_penalty: float | None = Field(None, description='存在惩罚')
    frequency_penalty: float | None = Field(None, description='频率惩罚')
    is_default: bool | None = Field(None, description='是否为用户默认 Agent')
    sort_order: int | None = Field(None, description='排序')
    visibility: str | None = Field(None, description='可见性 private/public/official')
    builtin_tools: dict | None = Field(None, description='内置工具配置')
    enable_sub_agents: bool | None = Field(None, description='允许动态生成子代理')


class GetAgentDetail(AgentSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Agent ID')
    user_id: int = Field(description='所有者 ID')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
