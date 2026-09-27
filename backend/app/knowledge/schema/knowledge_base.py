from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class KnowledgeBaseSchemaBase(SchemaBase):
    name: str = Field(description='Knowledge base name')
    description: str | None = Field(None, description='Description')
    embedding_model: str = Field(default='text-embedding-3-small', description='Embedding model')
    embedding_provider_id: int | None = Field(None, description='Embedding model LLM provider ID')
    chunk_size: int = Field(default=512, description='Chunk size')
    chunk_overlap: int = Field(default=50, description='Chunk overlap')
    status: str = Field(default='ready', description='Status ready/processing/error')
    visibility: str = Field(default='private', description='Visibility private/public/official')


class CreateKnowledgeBaseParam(KnowledgeBaseSchemaBase):
    pass


class UpdateKnowledgeBaseParam(SchemaBase):
    name: str | None = Field(None, description='Knowledge base name')
    description: str | None = Field(None, description='Description')
    embedding_model: str | None = Field(None, description='Embedding model')
    embedding_provider_id: int | None = Field(None, description='Embedding model LLM provider ID')
    chunk_size: int | None = Field(None, description='Chunk size')
    chunk_overlap: int | None = Field(None, description='Chunk overlap')
    status: str | None = Field(None, description='Status ready/processing/error')
    visibility: str | None = Field(None, description='Visibility private/public/official')


class GetKnowledgeBaseDetail(KnowledgeBaseSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Knowledge base ID')
    user_id: int = Field(description='Owner ID')
    document_count: int = Field(description='Document count')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
