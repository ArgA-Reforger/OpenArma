import type { LandmarkData } from '@/types/map'
import esES from './i18n/locales/es-ES.json'
import enUS from './i18n/locales/en-US.json'

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

// Maps a landmark type to its i18n key under `map.landmarkTypes` in the locale catalogs.
export const LANDMARK_TYPE_LABELS: Record<string, string> = {
  city: 'map.landmarkTypes.city',
  town: 'map.landmarkTypes.town',
  village: 'map.landmarkTypes.village',
  settlement: 'map.landmarkTypes.settlement',
  hill: 'map.landmarkTypes.hill',
  ridge: 'map.landmarkTypes.ridge',
  valley: 'map.landmarkTypes.valley',
  island: 'map.landmarkTypes.island',
  local: 'map.landmarkTypes.local',
  generic_name: 'map.landmarkTypes.generic_name',
  river: 'map.landmarkTypes.river',
  lake: 'map.landmarkTypes.lake',
  bay: 'map.landmarkTypes.bay',
  sea: 'map.landmarkTypes.sea',
  airport: 'map.landmarkTypes.airport',
  port: 'map.landmarkTypes.port',
  military_base: 'map.landmarkTypes.military_base',
  bunker: 'map.landmarkTypes.bunker',
  fortress: 'map.landmarkTypes.fortress',
  church: 'map.landmarkTypes.church',
  tower: 'map.landmarkTypes.tower',
  viewtower: 'map.landmarkTypes.viewtower',
  watertower: 'map.landmarkTypes.watertower',
  lighthouse: 'map.landmarkTypes.lighthouse',
  monument: 'map.landmarkTypes.monument',
  ruin: 'map.landmarkTypes.ruin',
  cave: 'map.landmarkTypes.cave',
  landmark: 'map.landmarkTypes.landmark',
  viewpoint: 'map.landmarkTypes.viewpoint',
  fuel_station: 'map.landmarkTypes.fuel_station',
  hospital: 'map.landmarkTypes.hospital',
  police_station: 'map.landmarkTypes.police_station',
  fire_station: 'map.landmarkTypes.fire_station',
  store: 'map.landmarkTypes.store',
  hotel: 'map.landmarkTypes.hotel',
  pub: 'map.landmarkTypes.pub',
  bus_stop: 'map.landmarkTypes.bus_stop',
  bus_station: 'map.landmarkTypes.bus_station',
  parking: 'map.landmarkTypes.parking',
  railway: 'map.landmarkTypes.railway',
  power_line: 'map.landmarkTypes.power_line',
  crossroad: 'map.landmarkTypes.crossroad',
  rock: 'map.landmarkTypes.rock',
  tree: 'map.landmarkTypes.tree',
  bush: 'map.landmarkTypes.bush',
  fence: 'map.landmarkTypes.fence',
  well: 'map.landmarkTypes.well',
  power_pole: 'map.landmarkTypes.power_pole',
  camp: 'map.landmarkTypes.camp',
  shelter: 'map.landmarkTypes.shelter',
  flag: 'map.landmarkTypes.flag',
  gate: 'map.landmarkTypes.gate',
  castle: 'map.landmarkTypes.castle',
  named_area: 'map.landmarkTypes.named_area',
  named_settlement: 'map.landmarkTypes.named_settlement',
  lake_named: 'map.landmarkTypes.lake_named',
  bay_named: 'map.landmarkTypes.bay_named',
  sea_named: 'map.landmarkTypes.sea_named',
}

const MAP_LOCALE_CATALOGS: Record<string, Record<string, unknown>> = {
  'es-ES': esES as Record<string, unknown>,
  'en-US': enUS as Record<string, unknown>,
}

function getCatalogLabel(key: string, locale: string): string | undefined {
  const catalog = MAP_LOCALE_CATALOGS[locale] ?? MAP_LOCALE_CATALOGS['en-US']
  let current: unknown = catalog
  for (const part of key.split('.')) {
    if (current == null || typeof current !== 'object') return undefined
    current = (current as Record<string, unknown>)[part]
  }
  return typeof current === 'string' ? current : undefined
}

export function getLandmarkDisplayName(lm: LandmarkData, locale: string): string {
  const isEs = locale.startsWith('es')
  const i18n = lm.name_i18n
  if (isEs && i18n?.es) return i18n.es
  if (i18n?.en) return i18n.en
  if (lm.name) return lm.name
  const key = LANDMARK_TYPE_LABELS[lm.type]
  const label = key ? getCatalogLabel(key, locale) : undefined
  if (label) return label
  return lm.type.replace(/_/g, ' ')
}
