import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class BattleSnapshot(Base):
    """Battle situation snapshot — stores a full battlefield frame on each heartbeat.

    Replaces SituationLog with structured storage, supporting:
    - AI vs AI fog of war filtering
    - Web real-time situation display
    - Post-battle review replay
    """

    __tablename__ = 'oa_battle_snapshot'

    id: Mapped[id_key] = mapped_column(init=False)
    project_id: Mapped[int] = mapped_column(sa.BigInteger, index=True, comment='Associated project ID')
    request_id: Mapped[int] = mapped_column(sa.Integer, comment='Heartbeat sequence number (frame)')
    conversation_group_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, index=True, default=None, comment='Associated conversation group ID'
    )
    game_time: Mapped[str | None] = mapped_column(sa.String(16), default=None, comment='In-game time HH:MM')
    timestamp: Mapped[int] = mapped_column(sa.BigInteger, default=0, comment='Unix timestamp')

    game_state: Mapped[dict | None] = mapped_column(
        sa.JSON, default=None, comment='Game state {game_mode, weather, visibility}'
    )
    units: Mapped[list | None] = mapped_column(
        sa.JSON,
        default=None,
        comment='All units [{entity_id, group_id, faction, position, life_state, health, weapon, ammo, ...}]',
    )
    groups: Mapped[list | None] = mapped_column(
        sa.JSON, default=None, comment='All squads [{id, faction, control, position, member_count, ...}]'
    )
    vehicles: Mapped[list | None] = mapped_column(
        sa.JSON, default=None, comment='All vehicles [{entity_id, faction, type, position, health, ...}]'
    )
    known_enemies: Mapped[list | None] = mapped_column(
        sa.JSON,
        default=None,
        comment='Perception data [{observer_group_id, observer_faction, target_entity_id, position, ...}]',
    )
    events: Mapped[list | None] = mapped_column(
        sa.JSON, default=None, comment='Frame events [{type, victim_id, killer_id, position, ...}]'
    )
    markers: Mapped[list | None] = mapped_column(
        sa.JSON, default=None, comment='Map markers [{id, type, position, text, faction, ...}]'
    )
    human_messages: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='Human messages')

    response_json: Mapped[dict | None] = mapped_column(
        sa.JSON, default=None, comment='AI response summary (all factions)'
    )
    processing_time_ms: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Processing duration (ms)')
