import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class ArmaConfig(Base):
    """Arma config table — one per conversation group (a project can have multiple)"""

    __tablename__ = 'oa_arma_config'

    id: Mapped[id_key] = mapped_column(init=False)
    project_id: Mapped[int] = mapped_column(sa.BigInteger, index=True, comment='Associated project ID')
    conversation_group_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, unique=True, default=None, index=True,
        comment='Conversation group ID — ID of the main Arma conversation',
    )
    enabled: Mapped[bool] = mapped_column(default=True, comment='Master switch')
    running: Mapped[bool] = mapped_column(default=False, comment='Running status (Web Start/Stop control)')

    sides: Mapped[list | None] = mapped_column(
        sa.JSON, default=None,
        comment='Faction configuration [{"faction":"US","control":"llm"}, {"faction":"USSR","control":"human"}]',
    )

    decision_interval: Mapped[float] = mapped_column(sa.Float, default=30.0, comment='Decision interval (seconds)')
    max_squads: Mapped[int] = mapped_column(sa.Integer, default=12, comment='Max squad count')
    emergency_enabled: Mapped[bool] = mapped_column(default=True, comment='Emergency detection switch')
    game_mode: Mapped[str] = mapped_column(
        sa.String(32), default='game_master', comment='Game mode game_master/conflict'
    )
    language: Mapped[str] = mapped_column(sa.String(8), default='en', comment='AI language en/zh')
    context_window: Mapped[int] = mapped_column(
        sa.Integer, default=15, comment='Context window size (last N messages)'
    )
    mission_objective: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='Mission objective JSON')

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