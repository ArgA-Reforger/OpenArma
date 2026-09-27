import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, id_key


class Conversation(Base, SoftDeleteMixin):
    """Conversation table"""

    __tablename__ = 'oa_conversation'

    id: Mapped[id_key] = mapped_column(init=False)
    project_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Project ID')
    user_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='User ID')
    title: Mapped[str | None] = mapped_column(sa.String(256), default=None, comment='Conversation title')
    agent_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='Bound Agent ID')
    topology_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, default=None, comment='Bound topology ID (mutually exclusive with agent_id)'
    )
    source: Mapped[str] = mapped_column(sa.String(32), default='web', comment='Source web/api/arma')
    side: Mapped[str | None] = mapped_column(
        sa.String(32), default=None, comment='Faction name null/US/USSR/FIA (AI vs AI)'
    )
    conversation_group_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        default=None,
        index=True,
        comment=(
            'Conversation group ID -- all conversations in the same group share this value (primary conversation ID)'
        ),
    )
    status: Mapped[str] = mapped_column(sa.String(32), default='active', comment='Status active/archived')
    mission_objective: Mapped[dict | None] = mapped_column(
        sa.JSON, default=None, comment='Mission objective JSON (independent per conversation/faction)'
    )
    is_pinned: Mapped[bool] = mapped_column(default=False, comment='Whether it is pinned')
    share_code: Mapped[str | None] = mapped_column(sa.String(36), default=None, unique=True, comment='Share code')
