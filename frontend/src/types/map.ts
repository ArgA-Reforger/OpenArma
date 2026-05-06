export interface GameMap {
  id: number
  name: string
  size_x: number
  size_z: number
  max_elevation: number
  description: string | null
  source: string | null
  format_version: string | null
  scanner_version: string | null
  scan_date: string | null
  status: string
  has_satellite_tiles: boolean
  tile_min_zoom: number
  tile_max_zoom: number
  created_time: string
}

export interface MapLayer {
  id: number
  map_id: number
  name: string
  layer_type: string
  image_path: string | null
  image_width_px: number | null
  image_height_px: number | null
  bound_left: number
  bound_bottom: number
  bound_right: number
  bound_top: number
  z_index: number
  opacity: number
  visible: boolean
  created_time: string
}

export interface LandmarkData {
  id: number
  name: string
  type: string
  position_x: number
  position_z: number
  tactical_value: string | null
  name_i18n?: Record<string, string> | null
}

export interface ZoneData {
  id: number
  name: string
  type: string
  center_x: number
  center_z: number
  radius: number
  building_count: number
}

export interface RoadData {
  id: number
  name: string | null
  type: string
  width: number
  length: number
  points: number[][]
}

export interface TileInfo {
  has_satellite_tiles: boolean
  tile_min_zoom: number
  tile_max_zoom: number
  available_zooms: number[]
  overview_grid_size: number
  tile_url_template: string
  tile_dir_exists: boolean
  tile_dir_path: string
}
