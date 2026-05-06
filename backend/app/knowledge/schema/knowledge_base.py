from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class KnowledgeBaseSchemaBase(SchemaBase):
    name: str = Field(description='知识库名称')
    description: str | None = Field(None, description='描述')
    embedding_model: str = Field(default='text-embedding-3-small', description='嵌入模型')
    embedding_provider_id: int | None = Field(None, description='嵌入模型 LLM 提供商 ID')
    chunk_size: int = Field(default=512, description='分块大小')
    chunk_overlap: int = Field(default=50, description='分块重叠')
    status: str = Field(default='ready', description='状态 ready/processing/error')
    visibility: str = Field(default='private', description='可见性 private/public/official')


class CreateKnowledgeBaseParam(KnowledgeBaseSchemaBase):
    pass


class UpdateKnowledgeBaseParam(SchemaBase):
    name: str | None = Field(None, description='知识库名称')
    description: str | None = Field(None, description='描述')
    embedding_model: str | None = Field(None, description='嵌入模型')
    embedding_provider_id: int | None = Field(None, description='嵌入模型 LLM 提供商 ID')
    chunk_size: int | None = Field(None, description='分块大小')
    chunk_overlap: int | None = Field(None, description='分块重叠')
    status: str | None = Field(None, description='状态 ready/processing/error')
    visibility: str | None = Field(None, description='可见性 private/public/official')


class GetKnowledgeBaseDetail(KnowledgeBaseSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='知识库 ID')
    user_id: int = Field(description='所有者 ID')
    document_count: int = Field(description='文档数量')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
