from datetime import datetime

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase


class CreateMapParam(SchemaBase):
    """从 Scanner JSON 导入地图的参数"""

    name: str = Field(description='地图名称')
    size_x: float = Field(description='地图宽度（米）')
    size_z: float = Field(description='地图深度（米）')
    max_elevation: float = Field(default=0, description='最大海拔（米）')
    offset_x: float = Field(default=0, description='X 偏移')
    offset_z: float = Field(default=0, description='Z 偏移')
    description: str | None = Field(None, description='地图描述')


class CreateMapManualParam(SchemaBase):
    """手动创建地图的参数"""

    name: str = Field(description='地图名称', min_length=1, max_length=64)
    size_x: float = Field(description='地图宽度（米）', gt=0)
    size_z: float = Field(description='地图深度（米）', gt=0)
    max_elevation: float = Field(default=0, description='最大海拔（米）')
    offset_x: float = Field(default=0, description='X 偏移')
    offset_z: float = Field(default=0, description='Z 偏移')
    description: str | None = Field(None, description='地图描述')


class UpdateMapParam(SchemaBase):
    description: str | None = Field(None, description='地图描述')
    status: str | None = Field(None, description='状态 draft/published')
    has_satellite_tiles: bool | None = Field(None, description='是否存在卫星瓦片')
    tile_min_zoom: int | None = Field(None, ge=0, le=10, description='瓦片最小缩放级别')
    tile_max_zoom: int | None = Field(None, ge=0, le=10, description='瓦片最大缩放级别')


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
    tactical_value: str | None = Field(None, description='战术价值 high/medium/low')
    tactical_description: str | None = Field(None, description='战术描述')
    tags: list | None = Field(None, description='标签列表')


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
    tactical_notes: str | None = Field(None, description='战术备注')
    boundary: list | None = Field(None, description='多边形边界')


class CreateLandmarkParam(SchemaBase):
    """手动添加地标"""

    name: str = Field(description='地标名称', min_length=1, max_length=128)
    type: str = Field(description='地标类型 (city/village/hill/military_base/...)', min_length=1)
    position_x: float = Field(description='世界坐标 X（米）')
    position_z: float = Field(description='世界坐标 Z（米）')
    position_y: float = Field(default=0, description='海拔（米）')
    description: str | None = Field(None, description='描述')
    tags: list[str] | None = Field(None, description='标签列表')


class CreateRoadParam(SchemaBase):
    """手动添加道路"""

    points: list[list[float]] = Field(description='路径点序列 [[x,z], ...]', min_length=2)
    name: str | None = Field(None, description='道路名称')
    type: str = Field(default='road', description='道路类型 main_road/secondary/track/path')
    width: float = Field(default=4.0, description='道路宽度（米）')


class CreateZoneParam(SchemaBase):
    """手动添加区域"""

    name: str = Field(description='区域名称', min_length=1, max_length=128)
    type: str = Field(description='区域类型 urban/suburban/forest/open_field/mountain/water')
    center_x: float = Field(description='中心坐标 X（米）')
    center_z: float = Field(description='中心坐标 Z（米）')
    radius: float = Field(default=250.0, description='区域半径（米）')
    boundary: list | None = Field(None, description='多边形边界')
    tactical_notes: str | None = Field(None, description='备注')


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
    """Scanner JSON 导入请求（接受完整 JSON 文件内容, 兼容 v1.0-v1.2）"""

    format_version: str = Field(description='格式版本')
    scanner_version: str = Field(description='扫描器版本')
    scan_date: str = Field(description='扫描时间')
    map: dict = Field(description='地图元信息 {name, size, offset, ...}')
    landmarks: list[dict] = Field(default_factory=list, description='地标列表')
    buildings: list[dict] = Field(default_factory=list, description='建筑列表 (legacy)')
    roads: list[dict] = Field(default_factory=list, description='道路列表')
    height_grid: dict | None = Field(None, description='高度网格数据')
    water_grid: dict | None = Field(None, description='水面网格数据 (v1.2)')
    zones: list[dict] = Field(default_factory=list, description='区域列表')
    entity_chunks: list[dict] = Field(default_factory=list, description='实体 chunk 引用 (v1.2)')
