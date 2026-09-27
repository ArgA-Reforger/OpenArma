import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, id_key


class KnowledgeBase(Base, SoftDeleteMixin):
    """Knowledge bases table"""

    __tablename__ = 'oa_knowledge_base'

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Owner ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='Knowledge base name')
    description: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='Description')
    embedding_model: Mapped[str] = mapped_column(
        sa.String(128), default='text-embedding-3-small', comment='Embedding model'
    )
    embedding_provider_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, default=None, comment='Embedding model LLM provider ID'
    )
    chunk_size: Mapped[int] = mapped_column(sa.Integer, default=512, comment='Chunk size')
    chunk_overlap: Mapped[int] = mapped_column(sa.Integer, default=50, comment='Chunk overlap')
    document_count: Mapped[int] = mapped_column(sa.Integer, default=0, init=False, comment='Document count')
    status: Mapped[str] = mapped_column(sa.String(32), default='ready', comment='Status ready/processing/error')
    visibility: Mapped[str] = mapped_column(
        sa.String(16), default='private', comment='Visibility private/public/official'
    )
