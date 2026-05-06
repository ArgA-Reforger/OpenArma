import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class ArmaConfig(Base):
    """Arma 配置表 — 每个对话组一条（同项目可有多条）"""

    __tablename__ = 'oa_arma_config'

    id: Mapped[id_key] = mapped_column(init=False)
    project_id: Mapped[int] = mapped_column(sa.BigInteger, index=True, comment='关联项目 ID')
    conversation_group_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, unique=True, default=None, index=True,
        comment='对话组标识 — 主 Arma 对话的 ID',
    )
    enabled: Mapped[bool] = mapped_column(default=True, comment='总控开关')
    running: Mapped[bool] = mapped_column(default=False, comment='运行状态（Web 端 Start/Stop 控制）')

    sides: Mapped[list | None] = mapped_column(
        sa.JSON, default=None,
        comment='阵营配置 [{"faction":"US","control":"llm"}, {"faction":"USSR","control":"human"}]',
    )

    decision_interval: Mapped[float] = mapped_column(sa.Float, default=30.0, comment='决策间隔（秒）')
    max_squads: Mapped[int] = mapped_column(sa.Integer, default=12, comment='最大小队数')
    emergency_enabled: Mapped[bool] = mapped_column(default=True, comment='紧急检测开关')
    game_mode: Mapped[str] = mapped_column(sa.String(32), default='game_master', comment='游戏模式 game_master/conflict')
    language: Mapped[str] = mapped_column(sa.String(8), default='en', comment='AI 语言 en/zh')
    context_window: Mapped[int] = mapped_column(sa.Integer, default=15, comment='上下文窗口大小（最近 N 条消息）')
    mission_objective: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='任务目标 JSON')

    @property
    def sides_list(self) -> list[dict]:
        """Return sides config with fallback defaults."""
        if self.sides:
            return self.sides
        return [
            {'faction': 'US', 'control': 'llm'},
            {'faction': 'USSR', 'control': 'human'},
        ]

    @property
    def llm_sides(self) -> list[dict]:
        """Return only LLM-controlled sides."""
        return [s for s in self.sides_list if s.get('control') == 'llm']