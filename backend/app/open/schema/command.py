from pydantic import BaseModel, Field


class SituationReportRequest(BaseModel):
    request_id: int
    timestamp: int
    conversation_id: str | None = None
    priority: str = 'normal'
    game_state: dict = Field(default_factory=dict)
    groups: list[dict] = Field(default_factory=list)
    units: list[dict] = Field(default_factory=list)
    vehicles: list[dict] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)
    markers: list[dict] = Field(default_factory=list)
    human_messages: list[dict] = Field(default_factory=list)
    mode_specific: dict = Field(default_factory=dict)


class PendingOrders(BaseModel):
    request_id: int
    orders: list[dict]
    briefing: str = ''
    assessment: str = ''
    priority_targets: list[str] = Field(default_factory=list)


class SideConfigBlock(BaseModel):
    faction: str
    control: str = 'llm'


class ArmaConfigBlock(BaseModel):
    running: bool = False
    decision_interval: float = 30.0
    sides: list[SideConfigBlock] = Field(default_factory=list)
    max_squads: int = 12
    emergency_enabled: bool = True
    language: str = 'en'


class CommandResponse(BaseModel):
    ack: bool = True
    request_id: int
    status: str
    pending_orders: PendingOrders | None = None
    config: ArmaConfigBlock | None = None
    web_messages: list[dict] = Field(default_factory=list)
    conversation_id: str
    error: str | None = None
