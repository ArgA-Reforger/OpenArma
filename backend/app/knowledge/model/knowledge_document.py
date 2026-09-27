import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, UniversalText, id_key


class KnowledgeDocument(Base, SoftDeleteMixin):
    """Knowledge base documents table"""

    __tablename__ = 'oa_knowledge_document'

    id: Mapped[id_key] = mapped_column(init=False)
    knowledge_base_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Knowledge base ID')
    title: Mapped[str] = mapped_column(sa.String(256), comment='Document title')
    source_type: Mapped[str] = mapped_column(sa.String(32), default='upload', comment='Source type upload/url/text')
    file_path: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='MinIO file path')
    file_size: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='File size (bytes)')
    content: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='Text content (text type)')
    metadata_: Mapped[dict | None] = mapped_column('metadata', sa.JSON(), default=None, comment='Document metadata')
    chunk_count: Mapped[int] = mapped_column(sa.Integer, default=0, init=False, comment='Chunk count')
    status: Mapped[str] = mapped_column(
        sa.String(32), default='pending', comment='Status pending/processing/ready/error'
    )
    error_message: Mapped[str | None] = mapped_column(
        sa.String(1024), default=None, init=False, comment='Error message'
    )
