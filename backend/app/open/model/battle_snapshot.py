import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class BattleSnapshot(Base):
    """战场态势快照 — 每次心跳存储一帧完整战场数据。

    替代 SituationLog，提供结构化存储，支持：
    - AI vs AI 战争迷雾过滤
    - Web 实时态势显示
    - 战后复盘回放
    """

    __tablename__ = 'oa_battle_snapshot'

    id: Mapped[id_key] = mapped_column(init=False)
    project_id: Mapped[int] = mapped_column(sa.BigInteger, index=True, comment='关联项目 ID')
    request_id: Mapped[int] = mapped_column(sa.Integer, comment='心跳序号（帧号）')
    conversation_group_id: Mapped[int | None] = mapped_column(sa.BigInteger, index=True, default=None, comment='关联对话组 ID')
    game_time: Mapped[str | None] = mapped_column(sa.String(16), default=None, comment='游戏内时间 HH:MM')
    timestamp: Mapped[int] = mapped_column(sa.BigInteger, default=0, comment='Unix 时间戳')

    game_state: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='游戏状态 {game_mode, weather, visibility}')
    units: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='所有士兵 [{entity_id, group_id, faction, position, life_state, health, weapon, ammo, ...}]')
    groups: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='所有小队 [{id, faction, control, position, member_count, ...}]')
    vehicles: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='所有载具 [{entity_id, faction, type, position, health, ...}]')
    known_enemies: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='感知数据 [{observer_group_id, observer_faction, target_entity_id, position, ...}]')
    events: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='本帧事件 [{type, victim_id, killer_id, position, ...}]')
    markers: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='地图标记 [{id, type, position, text, faction, ...}]')
    human_messages: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='人类消息')

    response_json: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='AI 响应汇总（所有阵营）')
    processing_time_ms: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='处理耗时(ms)')
