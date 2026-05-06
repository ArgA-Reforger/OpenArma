import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from backend.common.model import Base, id_key


class ProjectAgent(Base):
    __tablename__ = 'oa_project_agent'

    id: Mapped[id_key] = mapped_column(init=False)
    project_id: Mapped[int] = mapped_column(sa.BigInteger, comment='项目 ID')
    agent_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Agent ID')
    sort_order: Mapped[int] = mapped_column(sa.Integer, default=0, comment='排序')
