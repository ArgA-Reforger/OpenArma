import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, UniversalText, id_key


class KnowledgeDocument(Base, SoftDeleteMixin):
    """知识库文档表"""

    __tablename__ = 'oa_knowledge_document'

    id: Mapped[id_key] = mapped_column(init=False)
    knowledge_base_id: Mapped[int] = mapped_column(sa.BigInteger, comment='知识库 ID')
    title: Mapped[str] = mapped_column(sa.String(256), comment='文档标题')
    source_type: Mapped[str] = mapped_column(sa.String(32), default='upload', comment='来源类型 upload/url/text')
    file_path: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='MinIO 文件路径')
    file_size: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='文件大小(字节)')
    content: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='文本内容(text类型)')
    metadata_: Mapped[dict | None] = mapped_column('metadata', sa.JSON(), default=None, comment='文档元数据')
    chunk_count: Mapped[int] = mapped_column(sa.Integer, default=0, init=False, comment='分块数量')
    status: Mapped[str] = mapped_column(sa.String(32), default='pending', comment='状态 pending/processing/ready/error')
    error_message: Mapped[str | None] = mapped_column(sa.String(1024), default=None, init=False, comment='错误信息')
