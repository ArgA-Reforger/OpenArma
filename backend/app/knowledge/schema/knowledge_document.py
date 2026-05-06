from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class KnowledgeDocumentSchemaBase(SchemaBase):
    title: str = Field(description='文档标题')
    source_type: str = Field(default='upload', description='来源类型 upload/url/text')
    file_path: str | None = Field(None, description='MinIO 文件路径')
    file_size: int | None = Field(None, description='文件大小(字节)')
    content: str | None = Field(None, description='文本内容(text类型)')
    metadata: dict | None = Field(None, validation_alias='metadata_', description='文档元数据')


class CreateKnowledgeDocumentParam(KnowledgeDocumentSchemaBase):
    pass


class GetKnowledgeDocumentDetail(KnowledgeDocumentSchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='文档 ID')
    knowledge_base_id: int = Field(description='知识库 ID')
    chunk_count: int = Field(description='分块数量')
    status: str = Field(description='状态 pending/processing/ready/error')
    error_message: str | None = Field(None, description='错误信息')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
