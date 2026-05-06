import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, id_key


class Conversation(Base, SoftDeleteMixin):
    """对话表"""

    __tablename__ = 'oa_conversation'

    id: Mapped[id_key] = mapped_column(init=False)
    project_id: Mapped[int] = mapped_column(sa.BigInteger, comment='项目 ID')
    user_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='用户 ID')
    title: Mapped[str | None] = mapped_column(sa.String(256), default=None, comment='对话标题')
    agent_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='绑定 Agent ID')
    topology_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='绑定拓扑 ID（与 agent_id 互斥）')
    source: Mapped[str] = mapped_column(sa.String(32), default='web', comment='来源 web/api/arma')
    side: Mapped[str | None] = mapped_column(sa.String(32), default=None, comment='阵营名 null/US/USSR/FIA (AI vs AI)')
    conversation_group_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, default=None, index=True,
        comment='对话组 ID — 同一组内所有对话共享此值 (主对话 ID)',
    )
    status: Mapped[str] = mapped_column(sa.String(32), default='active', comment='状态 active/archived')
    mission_objective: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='任务目标 JSON（每个对话/阵营独立）')
    is_pinned: Mapped[bool] = mapped_column(default=False, comment='是否置顶')
    share_code: Mapped[str | None] = mapped_column(sa.String(36), default=None, unique=True, comment='分享码')
