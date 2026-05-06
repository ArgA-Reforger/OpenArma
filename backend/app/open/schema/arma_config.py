from datetime import datetime
from backend.common.enums import StrEnum

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class FactionEnum(StrEnum):
    US = 'US'
    USSR = 'USSR'
    FIA = 'FIA'
    CIV = 'CIV'
    RHS_USAF = 'RHS_USAF'
    RHS_AFRF = 'RHS_AFRF'
    RHS_ION = 'RHS_ION'
    MEI = 'MEI'
    MEC = 'MEC'


class ControlEnum(StrEnum):
    human = 'human'
    llm = 'llm'


class GameModeEnum(StrEnum):
    game_master = 'game_master'
    conflict = 'conflict'


class LanguageEnum(StrEnum):
    en = 'en'
    zh = 'zh'


class SideConfigItem(SchemaBase):
    faction: str = Field(..., description='阵营 key (US/USSR/FIA/...)')
    control: ControlEnum = ControlEnum.llm


class CreateArmaConfigParam(SchemaBase):
    enabled: bool = True
    sides: list[SideConfigItem] = Field(
        default_factory=lambda: [
            SideConfigItem(faction='US', control=ControlEnum.human),
            SideConfigItem(faction='USSR', control=ControlEnum.llm),
        ],
    )
    decision_interval: float = Field(default=30.0, ge=5.0, le=300.0)
    max_squads: int = Field(default=12, ge=1, le=50)
    emergency_enabled: bool = True
    game_mode: GameModeEnum = GameModeEnum.game_master
    language: LanguageEnum = LanguageEnum.en
    context_window: int = Field(default=15, ge=5, le=100, description='上下文窗口大小')
    mission_objective: dict | None = Field(None, description='任务目标 JSON')


class UpdateArmaConfigParam(SchemaBase):
    enabled: bool | None = None
    running: bool | None = None
    sides: list[SideConfigItem] | None = None
    decision_interval: float | None = Field(default=None, ge=5.0, le=300.0)
    max_squads: int | None = Field(default=None, ge=1, le=50)
    emergency_enabled: bool | None = None
    game_mode: GameModeEnum | None = None
    language: LanguageEnum | None = None
    context_window: int | None = Field(default=None, ge=5, le=100)
    mission_objective: dict | None = Field(None, description='任务目标 JSON')


class GetArmaConfigDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    conversation_group_id: int | None = None
    enabled: bool
    running: bool
    sides: list[dict] | None = None
    decision_interval: float
    max_squads: int
    emergency_enabled: bool
    game_mode: str
    language: str
    context_window: int
    mission_objective: dict | None = None
    created_time: datetime
    updated_time: datetime | None = None
