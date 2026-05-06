import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key

from pgvector.sqlalchemy import Vector


class GameMap(Base):
    """地图元信息表 — 通用地图系统，支持手动创建和 Scanner v1.2 导入"""

    __tablename__ = 'oa_map'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(64), unique=True, index=True, comment='地图名称')
    size_x: Mapped[float] = mapped_column(sa.Float, comment='画布宽度（米）')
    size_z: Mapped[float] = mapped_column(sa.Float, comment='画布高度（米）')
    max_elevation: Mapped[float] = mapped_column(sa.Float, default=0, comment='最大海拔（米）')
    offset_x: Mapped[float] = mapped_column(sa.Float, default=0, comment='地图起始 X 偏移')
    offset_z: Mapped[float] = mapped_column(sa.Float, default=0, comment='地图起始 Z 偏移')
    description: Mapped[str | None] = mapped_column(sa.Text, default=None, comment='地图描述')
    source: Mapped[str] = mapped_column(sa.String(16), default='manual', comment='数据来源 manual/scanner/import')
    # v1.2 extended metadata
    min_elevation: Mapped[float] = mapped_column(sa.Float, default=0, comment='最低海拔（米）')
    max_elevation_precise: Mapped[float] = mapped_column(sa.Float, default=0, comment='精确最高海拔')
    terrain_unit_scale: Mapped[float] = mapped_column(sa.Float, default=1.0, comment='地形单位缩放')
    has_ocean: Mapped[bool] = mapped_column(sa.Boolean, default=False, comment='是否有海洋')
    ocean_base_height: Mapped[float] = mapped_column(sa.Float, default=0, comment='海洋基础高度')
    world_bounds_min: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='世界边界最小值 [x,y,z]')
    world_bounds_max: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='世界边界最大值 [x,y,z]')
    total_entity_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='SubScene 0 实体总数')
    # Height grid
    height_grid_resolution: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='高度采样间隔（米）')
    height_grid_rows: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='高度网格行数')
    height_grid_cols: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='高度网格列数')
    height_grid_data: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='高度网格数据 [[float,...],...]')
    # Water grid (v1.3: [waterType, depth, lakeArea] per cell)
    water_grid_resolution: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='水面采样间隔（米）')
    water_grid_rows: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='水面网格行数')
    water_grid_cols: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='水面网格列数')
    water_grid_data: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='水面网格 [[[waterType,depth,lakeArea],...],...]  waterType: 0=none 1=ocean 2=pond 3=river')
    # Scanner metadata
    format_version: Mapped[str | None] = mapped_column(sa.String(8), default=None, comment='导入文件版本')
    scanner_version: Mapped[str | None] = mapped_column(sa.String(16), default=None, comment='扫描器版本')
    scan_date: Mapped[str | None] = mapped_column(sa.String(32), default=None, comment='扫描时间')
    status: Mapped[str] = mapped_column(sa.String(16), default='draft', comment='状态 draft/published')
    # Satellite tiles (EnfusionMapMaker output placed manually)
    has_satellite_tiles: Mapped[bool] = mapped_column(sa.Boolean, default=False, comment='是否存在卫星瓦片')
    tile_min_zoom: Mapped[int] = mapped_column(sa.Integer, default=0, comment='瓦片最小缩放级别')
    tile_max_zoom: Mapped[int] = mapped_column(sa.Integer, default=5, comment='瓦片最大缩放级别')
    stats_cache: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='地图统计缓存 {ocean_percent, vegetation_percent, elev_p2, elev_p98, ...}')


class MapLayer(Base):
    """Map image layer — multiple layers per canvas, each with position bounds."""

    __tablename__ = 'oa_map_layer'

    id: Mapped[id_key] = mapped_column(init=False)
    map_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey('oa_map.id'), index=True, comment='Parent map/canvas ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='Layer name')
    layer_type: Mapped[str] = mapped_column(sa.String(32), default='custom', comment='satellite/contour/terrain/tactical/custom')
    image_path: Mapped[str | None] = mapped_column(sa.String(256), default=None, comment='Image file path')
    image_width_px: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Image pixel width')
    image_height_px: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Image pixel height')
    bound_left: Mapped[float] = mapped_column(sa.Float, default=0, comment='Left edge X on canvas (meters)')
    bound_bottom: Mapped[float] = mapped_column(sa.Float, default=0, comment='Bottom edge Z on canvas (meters)')
    bound_right: Mapped[float] = mapped_column(sa.Float, default=0, comment='Right edge X on canvas (meters)')
    bound_top: Mapped[float] = mapped_column(sa.Float, default=0, comment='Top edge Z on canvas (meters)')
    z_index: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Stacking order')
    opacity: Mapped[float] = mapped_column(sa.Float, default=1.0, comment='Opacity 0-1')
    visible: Mapped[bool] = mapped_column(sa.Boolean, default=True, comment='Default visibility')


class MapLandmark(Base):
    """地图地标数据表"""

    __tablename__ = 'oa_map_landmark'

    id: Mapped[id_key] = mapped_column(init=False)
    map_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey('oa_map.id'), index=True, comment='关联地图 ID')
    type: Mapped[str] = mapped_column(sa.String(32), index=True, comment='地标类型')
    position_x: Mapped[float] = mapped_column(sa.Float, comment='世界坐标 X')
    position_z: Mapped[float] = mapped_column(sa.Float, comment='世界坐标 Z')
    name: Mapped[str] = mapped_column(sa.String(128), default='', comment='地标名称')
    descriptor_type_raw: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='原始枚举值')
    position_y: Mapped[float] = mapped_column(sa.Float, default=0, comment='海拔')
    faction_index: Mapped[int] = mapped_column(sa.Integer, default=0, comment='阵营 0=中立/1=东/2=西')
    info_text: Mapped[str | None] = mapped_column(sa.Text, default=None, comment='附加文本')
    group_type: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='分组类型')
    image_def: Mapped[str | None] = mapped_column(sa.String(64), default=None, comment='图标定义')
    # v1.2 fields
    base_type: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='基础类型枚举值')
    angle: Mapped[float] = mapped_column(sa.Float, default=0, comment='角度')
    range: Mapped[float] = mapped_column(sa.Float, default=0, comment='范围（米）')
    priority: Mapped[int] = mapped_column(sa.Integer, default=0, comment='优先级')
    links: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='关联地标名称列表')
    name_raw: Mapped[str | None] = mapped_column(sa.String(128), default=None, comment='原始 StringTable ID (如 #AR-MapLocation_XXX)')
    name_i18n: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='多语言地名 {"en":"...","zh":"..."}')
    # Tactical (user-annotated)
    tactical_value: Mapped[str | None] = mapped_column(sa.String(8), default=None, comment='战术价值 high/medium/low')
    tactical_description: Mapped[str | None] = mapped_column(sa.Text, default=None, comment='战术描述')
    tags: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='标签列表')


class MapEntity(Base):
    """地图实体详情表 — 从 chunk 文件导入的完整实体数据"""

    __tablename__ = 'oa_map_entity'

    id: Mapped[id_key] = mapped_column(init=False)
    map_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey('oa_map.id'), index=True, comment='关联地图 ID')
    category: Mapped[str] = mapped_column(sa.String(24), index=True, comment='分类 ~20类: tree/bush/grass/vegetation/rock/cliff/building*/fence/bridge/fortification/ruin/structure/vehicle_*/infrastructure/other')
    position_x: Mapped[float] = mapped_column(sa.Float, comment='世界坐标 X')
    position_z: Mapped[float] = mapped_column(sa.Float, comment='世界坐标 Z')
    position_y: Mapped[float] = mapped_column(sa.Float, default=0, comment='海拔 Y')
    size_x: Mapped[float] = mapped_column(sa.Float, default=0, comment='包围盒宽度')
    size_y: Mapped[float] = mapped_column(sa.Float, default=0, comment='包围盒高度')
    size_z: Mapped[float] = mapped_column(sa.Float, default=0, comment='包围盒深度')
    rotation: Mapped[float] = mapped_column(sa.Float, default=0, comment='Y轴旋转角度 (yaw, degrees)')
    corners: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='世界坐标四角点 [[x,z],[x,z],[x,z],[x,z]]')
    name: Mapped[str | None] = mapped_column(sa.String(128), default=None, comment='实体名称')
    prefab_path: Mapped[str | None] = mapped_column(sa.String(256), default=None, index=True, comment='Prefab 路径')
    chunk_name: Mapped[str | None] = mapped_column(sa.String(32), default=None, index=True, comment='所属 chunk 名称')
    source: Mapped[str] = mapped_column(sa.String(16), default='workbench', comment='数据来源 workbench/scanner/merged')


class MapRoad(Base):
    """地图道路网络表"""

    __tablename__ = 'oa_map_road'

    id: Mapped[id_key] = mapped_column(init=False)
    map_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey('oa_map.id'), index=True, comment='关联地图 ID')
    points: Mapped[list] = mapped_column(sa.JSON, comment='路径点序列 [[x,z], ...]')
    name: Mapped[str | None] = mapped_column(sa.String(128), default=None, comment='道路名称')
    type: Mapped[str] = mapped_column(sa.String(16), default='road', comment='道路类型 main_road/secondary/track/path')
    width: Mapped[float] = mapped_column(sa.Float, default=4.0, comment='道路宽度（米）')
    length: Mapped[float] = mapped_column(sa.Float, default=0, comment='道路长度（米）')


class MapZone(Base):
    """地图区域划分表"""

    __tablename__ = 'oa_map_zone'

    id: Mapped[id_key] = mapped_column(init=False)
    map_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey('oa_map.id'), index=True, comment='关联地图 ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='区域名称')
    type: Mapped[str] = mapped_column(sa.String(16), comment='区域类型 urban/suburban/rural/open_field')
    center_x: Mapped[float] = mapped_column(sa.Float, comment='中心坐标 X')
    center_z: Mapped[float] = mapped_column(sa.Float, comment='中心坐标 Z')
    radius: Mapped[float] = mapped_column(sa.Float, default=250.0, comment='区域半径（米）')
    building_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='建筑数量')
    tree_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='树木数量')
    rock_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='岩石数量')
    structure_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='结构体数量')
    vehicle_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='车辆数量')
    infrastructure_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='基础设施数量')
    other_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='其他实体数量')
    total_entities: Mapped[int] = mapped_column(sa.Integer, default=0, comment='实体总数')
    boundary: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='多边形边界')
    tactical_notes: Mapped[str | None] = mapped_column(sa.Text, default=None, comment='战术备注')


class HexCell(Base):
    """H3 六边形地形格子 — 预计算的地形特征，用于空间 RAG"""

    __tablename__ = 'oa_hex_cell'

    id: Mapped[id_key] = mapped_column(init=False)
    map_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey('oa_map.id'), index=True, comment='关联地图 ID')
    h3_index: Mapped[str] = mapped_column(sa.String(16), index=True, comment='H3 索引 (res-9)')
    center_x: Mapped[float] = mapped_column(sa.Float, comment='格子中心 X (世界坐标)')
    center_z: Mapped[float] = mapped_column(sa.Float, comment='格子中心 Z (世界坐标)')

    avg_height: Mapped[float] = mapped_column(sa.Float, default=0, comment='平均海拔')
    max_slope: Mapped[float] = mapped_column(sa.Float, default=0, comment='最大坡度 (度)')
    terrain_type: Mapped[str] = mapped_column(sa.String(24), default='open', comment='地形类型 ridgeline/hilltop/valley/riverbed/open_flat/forest_floor/forested_slope/steep_slope/forest/urban/suburban/water/open')
    building_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='建筑数量')
    tree_density: Mapped[float] = mapped_column(sa.Float, default=0, comment='树木密度 0-1')
    road_density: Mapped[float] = mapped_column(sa.Float, default=0, comment='道路密度 0-1')
    water_coverage: Mapped[float] = mapped_column(sa.Float, default=0, comment='水域覆盖率 0-1')

    cover_rating: Mapped[str] = mapped_column(sa.String(12), default='poor', comment='掩蔽评级 excellent/good/moderate/poor')
    trafficability: Mapped[str] = mapped_column(sa.String(16), default='easy', comment='通行性 easy/moderate/difficult/impassable')
    observation: Mapped[str] = mapped_column(sa.String(12), default='good', comment='观察条件 excellent/good/moderate/limited/poor')

    description: Mapped[str] = mapped_column(sa.Text, default='', comment='自然语言地形描述')
    embedding: Mapped[list | None] = mapped_column(Vector(), default=None, comment='描述向量 (embedding)')
