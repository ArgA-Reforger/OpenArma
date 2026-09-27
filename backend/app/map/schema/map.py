from datetime import datetime

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase


class CreateMapParam(SchemaBase):
    """Parameters for importing map from Scanner JSON"""

    name: str = Field(description='Map name')
    size_x: float = Field(description='Map width (meters)')
    size_z: float = Field(description='Map depth (meters)')
    max_elevation: float = Field(default=0, description='Max elevation (meters)')
    offset_x: float = Field(default=0, description='X offset')
    offset_z: float = Field(default=0, description='Z offset')
    description: str | None = Field(None, description='Map description')


class CreateMapManualParam(SchemaBase):
    """Parameters for manually creating map"""

    name: str = Field(description='Map name', min_length=1, max_length=64)
    size_x: float = Field(description='Map width (meters)', gt=0)
    size_z: float = Field(description='Map depth (meters)', gt=0)
    max_elevation: float = Field(default=0, description='Max elevation (meters)')
    offset_x: float = Field(default=0, description='X offset')
    offset_z: float = Field(default=0, description='Z offset')
    description: str | None = Field(None, description='Map description')


class UpdateMapParam(SchemaBase):
    description: str | None = Field(None, description='Map description')
    status: str | None = Field(None, description='Status draft/published')
    has_satellite_tiles: bool | None = Field(None, description='Whether satellite tiles exist')
    tile_min_zoom: int | None = Field(None, ge=0, le=10, description='Tile min zoom level')
    tile_max_zoom: int | None = Field(None, ge=0, le=10, description='Tile max zoom level')


class GetMapDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    size_x: float
    size_z: float
    max_elevation: float
    offset_x: float
    offset_z: float
    description: str | None
    source: str
    min_elevation: float = 0
    max_elevation_precise: float = 0
    terrain_unit_scale: float = 1.0
    has_ocean: bool = False
    ocean_base_height: float = 0
    world_bounds_min: list | None = None
    world_bounds_max: list | None = None
    total_entity_count: int = 0
    height_grid_resolution: int | None = None
    height_grid_rows: int | None = None
    height_grid_cols: int | None = None
    water_grid_resolution: int | None = None
    water_grid_rows: int | None = None
    water_grid_cols: int | None = None
    format_version: str | None = None
    scanner_version: str | None = None
    scan_date: str | None = None
    status: str
    has_satellite_tiles: bool = False
    tile_min_zoom: int = 0
    tile_max_zoom: int = 5
    created_time: datetime
    updated_time: datetime | None = None


class GetMapSummary(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    size_x: float
    size_z: float
    source: str
    status: str
    has_satellite_tiles: bool = False
    created_time: datetime


class GetLandmarkDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    map_id: int
    name: str
    type: str
    descriptor_type_raw: int | None
    position_x: float
    position_y: float
    position_z: float
    faction_index: int
    info_text: str | None
    base_type: int | None = None
    angle: float = 0
    range: float = 0
    priority: int = 0
    links: list | None = None
    name_raw: str | None = None
    name_i18n: dict | None = None
    tactical_value: str | None = None
    tactical_description: str | None = None
    tags: list | None = None


class UpdateLandmarkParam(SchemaBase):
    tactical_value: str | None = Field(None, description='Tactical value high/medium/low')
    tactical_description: str | None = Field(None, description='Tactical description')
    tags: list | None = Field(None, description='Tags list')


class GetRoadDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    map_id: int
    name: str | None
    type: str
    width: float
    points: list
    length: float


class GetZoneDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    map_id: int
    name: str
    type: str
    center_x: float
    center_z: float
    radius: float
    building_count: int
    tree_count: int = 0
    rock_count: int = 0
    structure_count: int = 0
    vehicle_count: int = 0
    infrastructure_count: int = 0
    other_count: int = 0
    total_entities: int = 0
    boundary: list | None = None
    tactical_notes: str | None = None


class UpdateZoneParam(SchemaBase):
    tactical_notes: str | None = Field(None, description='Tactical notes')
    boundary: list | None = Field(None, description='Polygon boundary')


class CreateLandmarkParam(SchemaBase):
    """Manually add landmark"""

    name: str = Field(description='Landmark name', min_length=1, max_length=128)
    type: str = Field(description='Landmark type (city/village/hill/military_base/...)', min_length=1)
    position_x: float = Field(description='World coordinate X (meters)')
    position_z: float = Field(description='World coordinate Z (meters)')
    position_y: float = Field(default=0, description='Elevation (meters)')
    description: str | None = Field(None, description='Description')
    tags: list[str] | None = Field(None, description='Tags list')


class CreateRoadParam(SchemaBase):
    """Manually add road"""

    points: list[list[float]] = Field(description='Waypoint sequence [[x,z], ...]', min_length=2)
    name: str | None = Field(None, description='Road name')
    type: str = Field(default='road', description='Road type main_road/secondary/track/path')
    width: float = Field(default=4.0, description='Road width (meters)')


class CreateZoneParam(SchemaBase):
    """Manually add zone"""

    name: str = Field(description='Zone name', min_length=1, max_length=128)
    type: str = Field(description='Zone type urban/suburban/forest/open_field/mountain/water')
    center_x: float = Field(description='Center coordinate X (meters)')
    center_z: float = Field(description='Center coordinate Z (meters)')
    radius: float = Field(default=250.0, description='Zone radius (meters)')
    boundary: list | None = Field(None, description='Polygon boundary')
    tactical_notes: str | None = Field(None, description='Notes')


class CreateLayerParam(SchemaBase):
    """Create a new layer on a map canvas."""

    name: str = Field(description='Layer name', min_length=1, max_length=128)
    layer_type: str = Field(default='custom', description='satellite/contour/terrain/tactical/custom')
    bound_left: float = Field(default=0, description='Left edge X on canvas (meters)')
    bound_bottom: float = Field(default=0, description='Bottom edge Z on canvas (meters)')
    bound_right: float = Field(description='Right edge X on canvas (meters)')
    bound_top: float = Field(description='Top edge Z on canvas (meters)')
    z_index: int = Field(default=0, description='Stacking order')
    opacity: float = Field(default=1.0, ge=0, le=1, description='Opacity')
    visible: bool = Field(default=True, description='Default visibility')

    @model_validator(mode='after')
    def validate_bounds(self):
        if self.bound_right <= self.bound_left:
            raise ValueError('bound_right must be greater than bound_left')
        if self.bound_top <= self.bound_bottom:
            raise ValueError('bound_top must be greater than bound_bottom')
        return self


class UpdateLayerParam(SchemaBase):
    name: str | None = Field(None, description='Layer name')
    layer_type: str | None = Field(None, description='Layer type')
    bound_left: float | None = Field(None, description='Left edge X')
    bound_bottom: float | None = Field(None, description='Bottom edge Z')
    bound_right: float | None = Field(None, description='Right edge X')
    bound_top: float | None = Field(None, description='Top edge Z')
    z_index: int | None = Field(None, description='Stacking order')
    opacity: float | None = Field(None, ge=0, le=1, description='Opacity')
    visible: bool | None = Field(None, description='Visibility')


class GetLayerDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    map_id: int
    name: str
    layer_type: str
    image_path: str | None
    image_width_px: int | None
    image_height_px: int | None
    bound_left: float
    bound_bottom: float
    bound_right: float
    bound_top: float
    z_index: int
    opacity: float
    visible: bool
    created_time: datetime


class GetEntityDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    map_id: int
    category: str
    position_x: float
    position_y: float
    position_z: float
    size_x: float = 0
    size_y: float = 0
    size_z: float = 0
    name: str | None = None
    prefab_path: str | None = None
    chunk_name: str | None = None
    source: str = 'workbench'


class MapImportRequest(SchemaBase):
    """Scanner JSON import request (accepts full JSON file content, compatible with v1.0-v1.2)"""

    format_version: str = Field(description='Format version')
    scanner_version: str = Field(description='Scanner version')
    scan_date: str = Field(description='Scan timestamp')
    map: dict = Field(description='Map metadata {name, size, offset, ...}')
    landmarks: list[dict] = Field(default_factory=list, description='Landmarks list')
    buildings: list[dict] = Field(default_factory=list, description='Buildings list (legacy)')
    roads: list[dict] = Field(default_factory=list, description='Roads list')
    height_grid: dict | None = Field(None, description='Height grid data')
    water_grid: dict | None = Field(None, description='Water grid data (v1.2)')
    zones: list[dict] = Field(default_factory=list, description='Zones list')
    entity_chunks: list[dict] = Field(default_factory=list, description='Entity chunk references (v1.2)')
