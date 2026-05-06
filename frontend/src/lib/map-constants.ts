import type { LandmarkData } from '@/types/map'

export const ZONE_COLORS: Record<string, string> = {
  urban: '#D32F2F',
  suburban: '#E65100',
  forest: '#2E7D32',
  open_field: '#F9A825',
  mountain: '#5D4037',
  water: '#1565C0',
  rural: '#8D6E63',
  area: '#546E7A',
}

export const ROAD_COLORS: Record<string, string> = {
  main_road: '#D32F2F',
  secondary: '#E65100',
  track: '#795548',
  path: '#4E342E',
  road: '#E65100',
}

export const LANDMARK_CHIP_COLORS: Record<string, string> = {
  poi: '#D32F2F',
  military_base: '#B71C1C',
  church: '#4A148C',
  viewtower: '#0D47A1',
  viewpoint: '#01579B',
  airport: '#1A237E',
  bunker: '#37474F',
  fortress: '#B71C1C',
  lighthouse: '#F57F17',
  city: '#212121',
  town: '#424242',
  village: '#616161',
  hospital: '#1B5E20',
  fuel_station: '#E65100',
}

export const ZONE_CHIP_COLORS: Record<string, string> = {
  urban: '#D32F2F',
  suburban: '#E65100',
  forest: '#2E7D32',
  open_field: '#F9A825',
  mountain: '#5D4037',
  water: '#1565C0',
  rural: '#8D6E63',
  area: '#546E7A',
}

export const ROAD_CHIP_COLORS: Record<string, string> = {
  main_road: '#D32F2F',
  secondary: '#E65100',
  track: '#795548',
  path: '#4E342E',
  road: '#E65100',
}

export const LANDMARK_TYPE_LABELS: Record<string, [string, string]> = {
  city: ['City', '城市'],
  town: ['Town', '城镇'],
  village: ['Village', '村庄'],
  settlement: ['Settlement', '聚落'],
  hill: ['Hill', '山丘'],
  ridge: ['Ridge', '山脊'],
  valley: ['Valley', '山谷'],
  island: ['Island', '岛屿'],
  local: ['Local', '地点'],
  generic_name: ['Place', '地名'],
  river: ['River', '河流'],
  lake: ['Lake', '湖泊'],
  bay: ['Bay', '海湾'],
  sea: ['Sea', '海域'],
  airport: ['Airport', '机场'],
  port: ['Port', '港口'],
  military_base: ['Military Base', '军事基地'],
  bunker: ['Bunker', '碉堡'],
  fortress: ['Fortress', '要塞'],
  church: ['Church', '教堂'],
  tower: ['Tower', '塔'],
  viewtower: ['View Tower', '瞭望塔'],
  watertower: ['Water Tower', '水塔'],
  lighthouse: ['Lighthouse', '灯塔'],
  monument: ['Monument', '纪念碑'],
  ruin: ['Ruin', '遗迹'],
  cave: ['Cave', '洞穴'],
  landmark: ['Landmark', '地标'],
  viewpoint: ['Viewpoint', '观景点'],
  fuel_station: ['Gas Station', '加油站'],
  hospital: ['Hospital', '医院'],
  police_station: ['Police', '警察局'],
  fire_station: ['Fire Dept', '消防局'],
  store: ['Store', '商店'],
  hotel: ['Hotel', '酒店'],
  pub: ['Pub', '酒吧'],
  bus_stop: ['Bus Stop', '公交站'],
  bus_station: ['Bus Station', '公交总站'],
  parking: ['Parking', '停车场'],
  railway: ['Railway', '铁路'],
  power_line: ['Power Line', '电力线'],
  crossroad: ['Crossroad', '十字路口'],
  rock: ['Rock', '岩石'],
  tree: ['Tree', '树木'],
  bush: ['Bush', '灌木'],
  fence: ['Fence', '围栏'],
  well: ['Well', '水井'],
  power_pole: ['Power Pole', '电线杆'],
  camp: ['Camp', '营地'],
  shelter: ['Shelter', '避难所'],
  flag: ['Flag', '旗帜'],
  gate: ['Gate', '大门'],
  castle: ['Castle', '城堡'],
  named_area: ['Named Area', '命名区域'],
  named_settlement: ['Named Settlement', '命名聚落'],
  lake_named: ['Lake', '湖泊'],
  bay_named: ['Bay', '海湾'],
  sea_named: ['Sea', '海域'],
}

export function getLandmarkDisplayName(lm: LandmarkData, locale: string): string {
  const isZh = locale.startsWith('zh')
  const i18n = lm.name_i18n
  if (isZh && i18n?.zh) return i18n.zh
  if (!isZh && i18n?.en) return i18n.en
  if (i18n?.en) return i18n.en
  if (lm.name) return lm.name
  const labels = LANDMARK_TYPE_LABELS[lm.type]
  if (labels) return isZh ? labels[1] : labels[0]
  return lm.type.replace(/_/g, ' ')
}
