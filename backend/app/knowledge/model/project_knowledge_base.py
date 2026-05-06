import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class ProjectKnowledgeBase(Base):
    """项目-知识库绑定表"""

    __tablename__ = 'oa_project_knowledge_base'

    id: Mapped[id_key] = mapped_column(init=False)
    project_id: Mapped[int] = mapped_column(sa.BigInteger, comment='项目 ID')
    knowledge_base_id: Mapped[int] = mapped_column(sa.BigInteger, comment='知识库 ID')
