from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class KnowledgeDocumentSchemaBase(SchemaBase):
    title: str = Field(description='Document title')
    source_type: str = Field(default='upload', description='Source type upload/url/text')
    file_path: str | None = Field(None, description='MinIO file path')
    file_size: int | None = Field(None, description='File size (bytes)')
    content: str | None = Field(None, description='Text content (text type)')
    metadata: dict | None = Field(None, validation_alias='metadata_', description='Document metadata')


class CreateKnowledgeDocumentParam(KnowledgeDocumentSchemaBase):
    pass


class GetKnowledgeDocumentDetail(KnowledgeDocumentSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Document ID')
    knowledge_base_id: int = Field(description='Knowledge base ID')
    chunk_count: int = Field(description='Chunk count')
    status: str = Field(description='Status pending/processing/ready/error')
    error_message: str | None = Field(None, description='Error message')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
