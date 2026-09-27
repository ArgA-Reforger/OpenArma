import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class ProjectKnowledgeBase(Base):
    """Project-knowledge base bindings table"""

    __tablename__ = 'oa_project_knowledge_base'

    id: Mapped[id_key] = mapped_column(init=False)
    project_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Project ID')
    knowledge_base_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Knowledge base ID')
