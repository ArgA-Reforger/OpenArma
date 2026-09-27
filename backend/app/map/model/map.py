import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key

from pgvector.sqlalchemy import Vector


class GameMap(Base):
    """Map metadata table — general map system, supports manual creation and Scanner v1.2 import"""

    __tablename__ = 'oa_map'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(64), unique=True, index=True, comment='Map name')
    size_x: Mapped[float] = mapped_column(sa.Float, comment='Canvas width (meters)')
    size_z: Mapped[float] = mapped_column(sa.Float, comment='Canvas height (meters)')
    max_elevation: Mapped[float] = mapped_column(sa.Float, default=0, comment='Max elevation (meters)')
    offset_x: Mapped[float] = mapped_column(sa.Float, default=0, comment='Map origin X offset')
    offset_z: Mapped[float] = mapped_column(sa.Float, default=0, comment='Map origin Z offset')
    description: Mapped[str | None] = mapped_column(sa.Text, default=None, comment='Map description')
    source: Mapped[str] = mapped_column(sa.String(16), default='manual', comment='Data source manual/scanner/import')
    # v1.2 extended metadata
    min_elevation: Mapped[float] = mapped_column(sa.Float, default=0, comment='Min elevation (meters)')
    max_elevation_precise: Mapped[float] = mapped_column(sa.Float, default=0, comment='Precise max elevation')
    terrain_unit_scale: Mapped[float] = mapped_column(sa.Float, default=1.0, comment='Terrain unit scale')
    has_ocean: Mapped[bool] = mapped_column(sa.Boolean, default=False, comment='Whether ocean exists')
    ocean_base_height: Mapped[float] = mapped_column(sa.Float, default=0, comment='Ocean base height')
    world_bounds_min: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='World bounds min [x,y,z]')
    world_bounds_max: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='World bounds max [x,y,z]')
    total_entity_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='SubScene 0 total entity count')
    # Height grid
    height_grid_resolution: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Height grid sampling interval (meters)')
    height_grid_rows: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Height grid rows')
    height_grid_cols: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Height grid columns')
    height_grid_data: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='Height grid data [[float,...],...]')
    # Water grid (v1.3: [waterType, depth, lakeArea] per cell)
    water_grid_resolution: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Water grid sampling interval (meters)')
    water_grid_rows: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Water grid rows')
    water_grid_cols: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Water grid columns')
    water_grid_data: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='Water grid [[[waterType,depth,lakeArea],...],...]  waterType: 0=none 1=ocean 2=pond 3=river')
    # Scanner metadata
    format_version: Mapped[str | None] = mapped_column(sa.String(8), default=None, comment='Imported file version')
    scanner_version: Mapped[str | None] = mapped_column(sa.String(16), default=None, comment='Scanner version')
    scan_date: Mapped[str | None] = mapped_column(sa.String(32), default=None, comment='Scan timestamp')
    status: Mapped[str] = mapped_column(sa.String(16), default='draft', comment='Status draft/published')
    # Satellite tiles (EnfusionMapMaker output placed manually)
    has_satellite_tiles: Mapped[bool] = mapped_column(sa.Boolean, default=False, comment='Whether satellite tiles exist')
    tile_min_zoom: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Tile min zoom level')
    tile_max_zoom: Mapped[int] = mapped_column(sa.Integer, default=5, comment='Tile max zoom level')
    stats_cache: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='Map statistics cache {ocean_percent, vegetation_percent, elev_p2, elev_p98, ...}')


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
    """Map landmarks table"""

    __tablename__ = 'oa_map_landmark'

    id: Mapped[id_key] = mapped_column(init=False)
    map_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey('oa_map.id'), index=True, comment='Associated map ID')
    type: Mapped[str] = mapped_column(sa.String(32), index=True, comment='Landmark type')
    position_x: Mapped[float] = mapped_column(sa.Float, comment='World coordinate X')
    position_z: Mapped[float] = mapped_column(sa.Float, comment='World coordinate Z')
    name: Mapped[str] = mapped_column(sa.String(128), default='', comment='Landmark name')
    descriptor_type_raw: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Raw enum value')
    position_y: Mapped[float] = mapped_column(sa.Float, default=0, comment='Elevation')
    faction_index: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Faction 0=neutral/1=east/2=west')
    info_text: Mapped[str | None] = mapped_column(sa.Text, default=None, comment='Additional text')
    group_type: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Group type')
    image_def: Mapped[str | None] = mapped_column(sa.String(64), default=None, comment='Icon definition')
    # v1.2 fields
    base_type: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Base type enum value')
    angle: Mapped[float] = mapped_column(sa.Float, default=0, comment='Angle')
    range: Mapped[float] = mapped_column(sa.Float, default=0, comment='Range (meters)')
    priority: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Priority')
    links: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='Associated landmark names list')
    name_raw: Mapped[str | None] = mapped_column(sa.String(128), default=None, comment='Raw StringTable ID (e.g. #AR-MapLocation_XXX)')
    name_i18n: Mapped[dict | None] = mapped_column(sa.JSON, default=None, comment='Multilingual place names {"en":"...","zh":"..."}')
    # Tactical (user-annotated)
    tactical_value: Mapped[str | None] = mapped_column(sa.String(8), default=None, comment='Tactical value high/medium/low')
    tactical_description: Mapped[str | None] = mapped_column(sa.Text, default=None, comment='Tactical description')
    tags: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='Tags list')


class MapEntity(Base):
    """Map entity details table — full entity data imported from chunk files"""

    __tablename__ = 'oa_map_entity'

    id: Mapped[id_key] = mapped_column(init=False)
    map_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey('oa_map.id'), index=True, comment='Associated map ID')
    category: Mapped[str] = mapped_column(sa.String(24), index=True, comment='Category ~20 types: tree/bush/grass/vegetation/rock/cliff/building*/fence/bridge/fortification/ruin/structure/vehicle_*/infrastructure/other')
    position_x: Mapped[float] = mapped_column(sa.Float, comment='World coordinate X')
    position_z: Mapped[float] = mapped_column(sa.Float, comment='World coordinate Z')
    position_y: Mapped[float] = mapped_column(sa.Float, default=0, comment='Elevation Y')
    size_x: Mapped[float] = mapped_column(sa.Float, default=0, comment='Bounding box width')
    size_y: Mapped[float] = mapped_column(sa.Float, default=0, comment='Bounding box height')
    size_z: Mapped[float] = mapped_column(sa.Float, default=0, comment='Bounding box depth')
    rotation: Mapped[float] = mapped_column(sa.Float, default=0, comment='Y-axis rotation angle (yaw, degrees)')
    corners: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='World coordinate four corners [[x,z],[x,z],[x,z],[x,z]]')
    name: Mapped[str | None] = mapped_column(sa.String(128), default=None, comment='Entity name')
    prefab_path: Mapped[str | None] = mapped_column(sa.String(256), default=None, index=True, comment='Prefab path')
    chunk_name: Mapped[str | None] = mapped_column(sa.String(32), default=None, index=True, comment='Belonging chunk name')
    source: Mapped[str] = mapped_column(sa.String(16), default='workbench', comment='Data source workbench/scanner/merged')


class MapRoad(Base):
    """Map road network table"""

    __tablename__ = 'oa_map_road'

    id: Mapped[id_key] = mapped_column(init=False)
    map_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey('oa_map.id'), index=True, comment='Associated map ID')
    points: Mapped[list] = mapped_column(sa.JSON, comment='Waypoint sequence [[x,z], ...]')
    name: Mapped[str | None] = mapped_column(sa.String(128), default=None, comment='Road name')
    type: Mapped[str] = mapped_column(sa.String(16), default='road', comment='Road type main_road/secondary/track/path')
    width: Mapped[float] = mapped_column(sa.Float, default=4.0, comment='Road width (meters)')
    length: Mapped[float] = mapped_column(sa.Float, default=0, comment='Road length (meters)')


class MapZone(Base):
    """Map zones table"""

    __tablename__ = 'oa_map_zone'

    id: Mapped[id_key] = mapped_column(init=False)
    map_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey('oa_map.id'), index=True, comment='Associated map ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='Zone name')
    type: Mapped[str] = mapped_column(sa.String(16), comment='Zone type urban/suburban/rural/open_field')
    center_x: Mapped[float] = mapped_column(sa.Float, comment='Center coordinate X')
    center_z: Mapped[float] = mapped_column(sa.Float, comment='Center coordinate Z')
    radius: Mapped[float] = mapped_column(sa.Float, default=250.0, comment='Zone radius (meters)')
    building_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Building count')
    tree_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Tree count')
    rock_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Rock count')
    structure_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Structure count')
    vehicle_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Vehicle count')
    infrastructure_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Infrastructure count')
    other_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Other entities count')
    total_entities: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Total entity count')
    boundary: Mapped[list | None] = mapped_column(sa.JSON, default=None, comment='Polygon boundary')
    tactical_notes: Mapped[str | None] = mapped_column(sa.Text, default=None, comment='Tactical notes')


class HexCell(Base):
    """H3 hexagonal terrain cells — precomputed terrain features for spatial RAG"""

    __tablename__ = 'oa_hex_cell'

    id: Mapped[id_key] = mapped_column(init=False)
    map_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey('oa_map.id'), index=True, comment='Associated map ID')
    h3_index: Mapped[str] = mapped_column(sa.String(16), index=True, comment='H3 index (res-9)')
    center_x: Mapped[float] = mapped_column(sa.Float, comment='Cell center X (world coordinate)')
    center_z: Mapped[float] = mapped_column(sa.Float, comment='Cell center Z (world coordinate)')

    avg_height: Mapped[float] = mapped_column(sa.Float, default=0, comment='Average elevation')
    max_slope: Mapped[float] = mapped_column(sa.Float, default=0, comment='Max slope (degrees)')
    terrain_type: Mapped[str] = mapped_column(sa.String(24), default='open', comment='Terrain type ridgeline/hilltop/valley/riverbed/open_flat/forest_floor/forested_slope/steep_slope/forest/urban/suburban/water/open')
    building_count: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Building count')
    tree_density: Mapped[float] = mapped_column(sa.Float, default=0, comment='Tree density 0-1')
    road_density: Mapped[float] = mapped_column(sa.Float, default=0, comment='Road density 0-1')
    water_coverage: Mapped[float] = mapped_column(sa.Float, default=0, comment='Water coverage 0-1')

    cover_rating: Mapped[str] = mapped_column(sa.String(12), default='poor', comment='Cover rating excellent/good/moderate/poor')
    trafficability: Mapped[str] = mapped_column(sa.String(16), default='easy', comment='Trafficability easy/moderate/difficult/impassable')
    observation: Mapped[str] = mapped_column(sa.String(12), default='good', comment='Observation condition excellent/good/moderate/limited/poor')

    description: Mapped[str] = mapped_column(sa.Text, default='', comment='Natural language terrain description')
    embedding: Mapped[list | None] = mapped_column(Vector(), default=None, comment='Description vector (embedding)')
