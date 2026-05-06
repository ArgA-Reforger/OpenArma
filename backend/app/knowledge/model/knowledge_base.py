import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, id_key


class KnowledgeBase(Base, SoftDeleteMixin):
    """知识库表"""

    __tablename__ = 'oa_knowledge_base'

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, comment='所有者 ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='知识库名称')
    description: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='描述')
    embedding_model: Mapped[str] = mapped_column(sa.String(128), default='text-embedding-3-small', comment='嵌入模型')
    embedding_provider_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='嵌入模型 LLM 提供商 ID')
    chunk_size: Mapped[int] = mapped_column(sa.Integer, default=512, comment='分块大小')
    chunk_overlap: Mapped[int] = mapped_column(sa.Integer, default=50, comment='分块重叠')
    document_count: Mapped[int] = mapped_column(sa.Integer, default=0, init=False, comment='文档数量')
    status: Mapped[str] = mapped_column(sa.String(32), default='ready', comment='状态 ready/processing/error')
    visibility: Mapped[str] = mapped_column(sa.String(16), default='private', comment='可见性 private/public/official')
