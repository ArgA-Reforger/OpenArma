'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Crosshair, ZoomIn, ZoomOut, Maximize, Mountain, ChevronDown, ChevronUp, Info } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import type { LandmarkData, ZoneData, RoadData } from '@/types/map'
import { ZONE_COLORS, ROAD_COLORS, getLandmarkDisplayName } from '@/lib/map-constants'
import { LayerControlPanel, type ThematicLayerData, type InteractiveMode, type BaseMapMode } from './layer-control-panel'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { getBackendOrigin } from '@/lib/api'

const MAX_ZOOM = 5
const TILE_SIZE = 256

interface DataLayerVisibility {
  landmarks: boolean
  roads: boolean
  zones: boolean
  grid: boolean
}

interface MapStatsData {
  map_name: string
  size_x: number
  size_z: number
  area_km2: number
  land_area_km2: number
  elevation_min: number
  elevation_max: number
  has_ocean: boolean
  ocean_percent: number
  avg_slope: number
  max_slope: number
  total_entities: number
  vegetation_count: number
  vegetation_coverage_pct: number
  urban_coverage_pct: number
  building_count: number
  landmark_count: number
  road_count: number
  road_total_km: number
  road_density_km_per_km2: number
  zone_count: number
  hex_cell_count: number
  terrain_distribution: Record<string, number>
  cover_distribution: Record<string, number>
  trafficability_distribution: Record<string, number>
  entity_by_category: Record<string, number>
}

function distToPercent(
  dist: Record<string, number>,
  labelFn?: (key: string) => string,
): [string, string][] {
  const total = Object.values(dist).reduce((s, v) => s + v, 0)
  if (total === 0) return []
  return Object.entries(dist)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([k, v]) => [labelFn ? labelFn(k) : k, `${Math.round(100 * v / total)}%`])
}

function MapInfoCard({ mapId, mapName }: { mapId: number; mapName?: string }) {
  const api = useApi()
  const { t } = useI18n()
  const [expanded, setExpanded] = useState(false)

  const { data: stats } = useQuery<MapStatsData>({
    queryKey: ['map-stats', mapId],
    queryFn: () => api.get(`/maps/admin/maps/${mapId}/stats`),
    enabled: !!mapId,
    staleTime: 5 * 60 * 1000,
  })

  if (!stats) return null

  const rows: [string, string][] = [
    [t('mapInfo.area'), `${stats.size_x.toLocaleString()} × ${stats.size_z.toLocaleString()}m (${stats.area_km2}km²)`],
    [t('mapInfo.landArea'), `${stats.land_area_km2}km²`],
    [t('mapInfo.elevation'), `${Math.round(stats.elevation_min)} ~ ${Math.round(stats.elevation_max)}m`],
    ...(stats.has_ocean ? [[t('mapInfo.ocean'), `${stats.ocean_percent}%`] as [string, string]] : []),
    [t('mapInfo.slope'), `${t('mapInfo.avg')} ${stats.avg_slope}° / ${t('mapInfo.max')} ${stats.max_slope}°`],
    [t('mapInfo.vegCoverage'), `${stats.vegetation_coverage_pct}%`],
    [t('mapInfo.urbanCoverage'), `${stats.urban_coverage_pct}%`],
    [t('mapInfo.vegetation'), `${stats.vegetation_count.toLocaleString()}`],
    [t('mapInfo.buildings'), stats.building_count.toLocaleString()],
    [t('mapInfo.roads'), `${stats.road_count} / ${stats.road_total_km}km`],
    [t('mapInfo.roadDensity'), `${stats.road_density_km_per_km2} km/km²`],
    [t('mapInfo.landmarks'), stats.landmark_count.toLocaleString()],
    [t('mapInfo.zones'), stats.zone_count.toLocaleString()],
    [t('mapInfo.entities'), stats.total_entities.toLocaleString()],
  ]

  const terrainTop = distToPercent(stats.terrain_distribution, (k) => t(`mapInfo.tt.${k}`))
  const coverTop = distToPercent(stats.cover_distribution, (k) => t(`mapInfo.cr.${k}`))
  const trafTop = distToPercent(stats.trafficability_distribution, (k) => t(`mapInfo.tf.${k}`))

  return (
    <div className="absolute bottom-3 right-3 z-[1000] max-h-[70vh] overflow-y-auto">
      <div className="bg-background/80 backdrop-blur-sm border rounded-lg shadow-lg overflow-hidden min-w-[220px]">
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-between gap-2 px-3 py-1.5 hover:bg-muted/50 transition-colors"
        >
          <div className="flex items-center gap-1.5">
            <Info className="h-3 w-3 text-muted-foreground" />
            <span className="text-xs font-medium">{mapName || stats.map_name}</span>
          </div>
          {expanded ? <ChevronDown className="h-3 w-3 text-muted-foreground" /> : <ChevronUp className="h-3 w-3 text-muted-foreground" />}
        </button>
        {expanded && (
          <div className="px-3 pb-2 pt-0.5 border-t">
            <div className="space-y-0.5">
              {rows.map(([label, value]) => (
                <div key={label} className="flex justify-between gap-4 text-[10px] text-muted-foreground">
                  <span className="shrink-0">{label}</span>
                  <span className="font-mono text-right">{value}</span>
                </div>
              ))}
            </div>

            {stats.hex_cell_count > 0 && (
              <>
                <div className="mt-1.5 pt-1 border-t">
                  <p className="text-[9px] font-medium text-muted-foreground/70 uppercase tracking-wider mb-0.5">{t('mapInfo.terrain')}</p>
                  {terrainTop.map(([k, v]) => (
                    <div key={k} className="flex justify-between text-[10px] text-muted-foreground">
                      <span>{k}</span><span className="font-mono">{v}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-1 pt-1 border-t">
                  <p className="text-[9px] font-medium text-muted-foreground/70 uppercase tracking-wider mb-0.5">{t('mapInfo.cover')}</p>
                  {coverTop.map(([k, v]) => (
                    <div key={k} className="flex justify-between text-[10px] text-muted-foreground">
                      <span>{k}</span><span className="font-mono">{v}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-1 pt-1 border-t">
                  <p className="text-[9px] font-medium text-muted-foreground/70 uppercase tracking-wider mb-0.5">{t('mapInfo.trafficability')}</p>
                  {trafTop.map(([k, v]) => (
                    <div key={k} className="flex justify-between text-[10px] text-muted-foreground">
                      <span>{k}</span><span className="font-mono">{v}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

interface ReforgerMapViewerProps {
  mapId: number
  mapName?: string
  canvasWidth: number
  canvasHeight: number
  offsetX?: number
  offsetZ?: number
  tileUrlTemplate: string
  tileMinZoom?: number
  tileMaxZoom?: number
  overviewGridSize?: number
  tileStepSize?: number
  satelliteTileUrl?: string
  landmarks?: LandmarkData[]
  zones?: ZoneData[]
  roads?: RoadData[]
  showLandmarks?: boolean
  showZones?: boolean
  showRoads?: boolean
  showGrid?: boolean
  locale?: string
  mapId_forLayers?: number
  hasMilitaryTiles?: boolean
  hasSatelliteTiles?: boolean
  baseMapMode?: BaseMapMode
  onBaseMapChange?: (mode: BaseMapMode) => void
  dataLayerVisibility?: DataLayerVisibility
  onDataLayerChange?: (layer: keyof DataLayerVisibility, visible: boolean) => void
  hiddenLandmarkTypes?: Set<string>
  onToggleLandmarkType?: (type: string) => void
  landmarkTypes?: [string, number][]
  hiddenRoadTypes?: Set<string>
  onToggleRoadType?: (type: string) => void
  roadTypes?: [string, number][]
  hiddenZoneTypes?: Set<string>
  onToggleZoneType?: (type: string) => void
  zoneTypes?: [string, number][]
  analysisTiles?: Record<string, { ready: boolean; zooms: number[]; url_template: string }>
  onMapReady?: (map: L.Map) => void
  onMapDestroy?: () => void
}

function buildCustomCRS(tileStepSize: number) {
  const scale = TILE_SIZE / (tileStepSize * Math.pow(2, MAX_ZOOM))
  return L.Util.extend({}, L.CRS, {
    projection: L.Projection.LonLat,
    transformation: new L.Transformation(scale, 0, -scale, 0),
    scale(zoom: number) { return Math.pow(2, zoom) },
    zoom(s: number) { return Math.log(s) / Math.LN2 },
    distance(a: L.LatLng, b: L.LatLng) {
      const dx = b.lng - a.lng
      const dy = b.lat - a.lat
      return Math.sqrt(dx * dx + dy * dy)
    },
    infinite: true,
  }) as unknown as L.CRS
}

function gameCoordsToLatLng(x: number, z: number, offset: number): L.LatLng {
  return L.latLng(z + offset, x + offset)
}

const InvertedYTileLayer = L.TileLayer.extend({
  getTileUrl(coords: L.Coords) {
    const invertedCoords = Object.create(coords)
    invertedCoords.y = -(coords.y + 1)
    return L.TileLayer.prototype.getTileUrl.call(this, invertedCoords)
  },
}) as new (url: string, options?: L.TileLayerOptions) => L.TileLayer

export function ReforgerMapViewer({
  mapId,
  mapName,
  canvasWidth,
  canvasHeight,
  offsetX = 0,
  offsetZ = 0,
  tileUrlTemplate,
  tileMinZoom = 0,
  tileMaxZoom = MAX_ZOOM,
  overviewGridSize = 3,
  tileStepSize = 100,
  satelliteTileUrl,
  landmarks = [],
  zones = [],
  roads = [],
  showLandmarks = true,
  showZones = false,
  showRoads = true,
  showGrid = true,
  locale = 'en-US',
  mapId_forLayers,
  hasMilitaryTiles = false,
  hasSatelliteTiles = false,
  baseMapMode = 'military',
  onBaseMapChange,
  dataLayerVisibility,
  onDataLayerChange,
  hiddenLandmarkTypes,
  onToggleLandmarkType,
  landmarkTypes,
  hiddenRoadTypes,
  onToggleRoadType,
  roadTypes,
  hiddenZoneTypes,
  onToggleZoneType,
  zoneTypes,
  analysisTiles,
  onMapReady,
  onMapDestroy,
}: ReforgerMapViewerProps) {
  const mapRef = useRef<L.Map | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [cursorCoord, setCursorCoord] = useState<{ x: number; z: number; grid: string; elev?: number } | null>(null)
  const [currentZoom, setCurrentZoom] = useState(0)
  const heightGridRef = useRef<{ grid: number[][]; resolution: number; rows: number; cols: number } | null>(null)
  const api = useApi()
  const thematicLayersRef = useRef<Map<string, L.LayerGroup>>(new Map())
  const thematicOpacityRef = useRef<Map<string, number>>(new Map())
  const [interactiveMode, setInteractiveMode] = useState<InteractiveMode>('none')
  const [interactiveClick, setInteractiveClick] = useState<{ x: number; z: number } | null>(null)
  const interactiveModeRef = useRef<InteractiveMode>('none')
  const satelliteLayerRef = useRef<L.TileLayer | null>(null)

  const cameraOffset = 0

  const crs = useMemo(() => buildCustomCRS(tileStepSize), [tileStepSize])

  const bounds = useMemo(() => {
    const min = gameCoordsToLatLng(0, 0, cameraOffset)
    const max = gameCoordsToLatLng(canvasWidth, canvasHeight, cameraOffset)
    return L.latLngBounds(min, max)
  }, [canvasWidth, canvasHeight, cameraOffset])

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = L.map(containerRef.current, {
      crs,
      zoom: 0,
      center: bounds.getCenter(),
      zoomControl: false,
      attributionControl: false,
      zoomSnap: 0.5,
      zoomDelta: 0.5,
      wheelPxPerZoomLevel: 240,
    })

    const tileLayer = new InvertedYTileLayer(tileUrlTemplate, {
      maxZoom: tileMaxZoom,
      minZoom: tileMinZoom,
      zoomReverse: true,
      bounds,
      tileSize: TILE_SIZE,
      updateWhenZooming: false,
      keepBuffer: 3,
      noWrap: true,
      crossOrigin: 'anonymous',
    })
    tileLayer.addTo(map)

    map.setMaxBounds(bounds.pad(0.2))

    map.on('mousemove', (e: L.LeafletMouseEvent) => {
      const gameX = Math.round(e.latlng.lng - cameraOffset)
      const gameZ = Math.round(e.latlng.lat - cameraOffset)
      const gridE = String(Math.max(0, Math.floor(gameX / 100))).padStart(3, '0')
      const gridN = String(Math.max(0, Math.floor(gameZ / 100))).padStart(3, '0')
      let elev: number | undefined
      const hg = heightGridRef.current
      if (hg) {
        const col = Math.min(Math.max(0, Math.floor(gameX / hg.resolution)), hg.cols - 1)
        const row = Math.min(Math.max(0, Math.floor(gameZ / hg.resolution)), hg.rows - 1)
        elev = hg.grid[row]?.[col]
      }
      setCursorCoord({ x: gameX, z: gameZ, grid: `${gridE}${gridN}`, elev })
    })

    map.on('zoomend', () => setCurrentZoom(map.getZoom()))

    map.on('click', (e: L.LeafletMouseEvent) => {
      if (interactiveModeRef.current === 'none') return
      const gameX = Math.round(e.latlng.lng - cameraOffset)
      const gameZ = Math.round(e.latlng.lat - cameraOffset)
      setInteractiveClick({ x: gameX, z: gameZ })
    })

    if (satelliteTileUrl) {
      const satLayer = new InvertedYTileLayer(satelliteTileUrl, {
        maxZoom: tileMaxZoom,
        minZoom: tileMinZoom,
        zoomReverse: true,
        bounds,
        tileSize: TILE_SIZE,
        noWrap: true,
        crossOrigin: 'anonymous',
        opacity: 0,
      })
      satLayer.addTo(map)
      satelliteLayerRef.current = satLayer
    }

    mapRef.current = map
    setCurrentZoom(map.getZoom())
    onMapReady?.(map)

    return () => {
      onMapDestroy?.()
      tileLayersRef.current.forEach(l => map.removeLayer(l))
      tileLayersRef.current.clear()
      thematicLayersRef.current.forEach(l => map.removeLayer(l))
      thematicLayersRef.current.clear()
      map.remove()
      mapRef.current = null
      satelliteLayerRef.current = null
    }
  }, [crs, tileUrlTemplate, satelliteTileUrl, tileMinZoom, tileMaxZoom, bounds, cameraOffset])

  useEffect(() => {
    let cancelled = false
    api.get<{ grid: number[][]; resolution: number; rows: number; cols: number }>(
      `/maps/admin/maps/${mapId}/heightmap`,
    ).then((data) => {
      if (!cancelled && data?.grid) heightGridRef.current = data
    }).catch(() => { /* no height data available */ })
    return () => { cancelled = true }
  }, [mapId, api])

  const landmarkLayerRef = useRef<L.LayerGroup | null>(null)
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    if (landmarkLayerRef.current) {
      map.removeLayer(landmarkLayerRef.current)
    }

    if (!showLandmarks || landmarks.length === 0) {
      landmarkLayerRef.current = null
      return
    }

    type SymbolDef = { symbol: string; bg: string; fg: string; size: number }
    const LANDMARK_SYMBOLS: Record<string, SymbolDef> = {
      city:             { symbol: '●', bg: '#212121', fg: '#fff', size: 20 },
      town:             { symbol: '●', bg: '#424242', fg: '#fff', size: 16 },
      village:          { symbol: '●', bg: '#616161', fg: '#fff', size: 12 },
      settlement:       { symbol: '●', bg: '#616161', fg: '#fff', size: 12 },
      named_settlement: { symbol: '●', bg: '#616161', fg: '#fff', size: 12 },
      military_base:    { symbol: '⬟', bg: '#B71C1C', fg: '#fff', size: 16 },
      bunker:           { symbol: '◆', bg: '#B71C1C', fg: '#fff', size: 14 },
      fortress:         { symbol: '⬟', bg: '#B71C1C', fg: '#fff', size: 16 },
      camp:             { symbol: '▲', bg: '#B71C1C', fg: '#fff', size: 14 },
      airport:          { symbol: '✈', bg: '#1A237E', fg: '#fff', size: 16 },
      port:             { symbol: '⚓', bg: '#0D47A1', fg: '#fff', size: 14 },
      hospital:         { symbol: '✚', bg: '#1B5E20', fg: '#fff', size: 14 },
      fuel_station:     { symbol: '⛽', bg: '#E65100', fg: '#fff', size: 14 },
      church:           { symbol: '†', bg: '#4A148C', fg: '#fff', size: 14 },
      castle:           { symbol: '🏰', bg: '#5D4037', fg: '#fff', size: 14 },
      lighthouse:       { symbol: '◉', bg: '#F57F17', fg: '#000', size: 14 },
      viewtower:        { symbol: '◎', bg: '#0D47A1', fg: '#fff', size: 14 },
      viewpoint:        { symbol: '◎', bg: '#01579B', fg: '#fff', size: 12 },
      named_area:       { symbol: '□', bg: '#546E7A', fg: '#fff', size: 12 },
      lake_named:       { symbol: '~', bg: '#1565C0', fg: '#fff', size: 12 },
      bay_named:        { symbol: '~', bg: '#1565C0', fg: '#fff', size: 12 },
      sea_named:        { symbol: '~', bg: '#0D47A1', fg: '#fff', size: 14 },
    }
    const DEFAULT_SYMBOL: SymbolDef = { symbol: '•', bg: '#37474F', fg: '#fff', size: 12 }

    const group = L.layerGroup()
    landmarks.forEach((lm) => {
      const hasName = !!(lm.name || lm.name_i18n?.en)
      if (!hasName) return

      const pos = gameCoordsToLatLng(lm.position_x, lm.position_z, cameraOffset)
      const displayName = getLandmarkDisplayName(lm, locale)
      const sym = LANDMARK_SYMBOLS[lm.type] || DEFAULT_SYMBOL

      const icon = L.divIcon({
        className: '',
        html: `<div style="
          width:${sym.size}px;height:${sym.size}px;
          background:${sym.bg};color:${sym.fg};
          border:1.5px solid #000;border-radius:2px;
          display:flex;align-items:center;justify-content:center;
          font-size:${Math.round(sym.size * 0.6)}px;line-height:1;
          font-weight:bold;
        ">${sym.symbol}</div>`,
        iconSize: [sym.size, sym.size],
        iconAnchor: [sym.size / 2, sym.size / 2],
      })

      const marker = L.marker(pos, { icon })

      marker.bindTooltip(displayName, {
        permanent: true,
        direction: 'right',
        offset: [sym.size / 2 + 4, 0],
        className: 'reforger-place-label',
      })

      group.addLayer(marker)
    })
    group.addTo(map)
    landmarkLayerRef.current = group
  }, [landmarks, showLandmarks, cameraOffset, locale])

  const zoneLayerRef = useRef<L.LayerGroup | null>(null)
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    if (zoneLayerRef.current) {
      map.removeLayer(zoneLayerRef.current)
    }

    if (!showZones || zones.length === 0) {
      zoneLayerRef.current = null
      return
    }

    const group = L.layerGroup()
    zones.forEach((zone) => {
      const color = ZONE_COLORS[zone.type] || '#6b7280'
      const r = zone.radius
      const sw = gameCoordsToLatLng(zone.center_x - r, zone.center_z - r, cameraOffset)
      const ne = gameCoordsToLatLng(zone.center_x + r, zone.center_z + r, cameraOffset)
      const rect = L.rectangle(L.latLngBounds(sw, ne), {
        color,
        fillColor: color,
        fillOpacity: 0.12,
        weight: 1.5,
        dashArray: '6,4',
      })
      if (zone.name) {
        rect.bindTooltip(zone.name, {
          permanent: true,
          direction: 'center',
          className: 'reforger-zone-label',
        })
      }
      group.addLayer(rect)
    })
    group.addTo(map)
    zoneLayerRef.current = group
  }, [zones, showZones, cameraOffset])

  const roadLayerRef = useRef<L.LayerGroup | null>(null)
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    if (roadLayerRef.current) {
      map.removeLayer(roadLayerRef.current)
    }

    if (!showRoads || roads.length === 0) {
      roadLayerRef.current = null
      return
    }

    const ROAD_STYLE: Record<string, { weight: number; opacity: number; dashArray?: string }> = {
      main_road: { weight: 4, opacity: 0.9 },
      secondary: { weight: 3, opacity: 0.85 },
      track: { weight: 2, opacity: 0.7, dashArray: '8 6' },
      path: { weight: 1.5, opacity: 0.6, dashArray: '2 4' },
    }

    const group = L.layerGroup()
    roads.forEach((road) => {
      const latLngs = road.points.map((p) => gameCoordsToLatLng(p[0], p.length >= 3 ? p[2] : p[1], cameraOffset))
      const color = ROAD_COLORS[road.type] || '#d97706'
      const style = ROAD_STYLE[road.type] || ROAD_STYLE.secondary
      const polyline = L.polyline(latLngs, {
        color,
        weight: style.weight,
        opacity: style.opacity,
        dashArray: style.dashArray,
      })
      if (road.name) {
        polyline.bindTooltip(road.name, { sticky: true })
      }
      group.addLayer(polyline)
    })
    group.addTo(map)
    roadLayerRef.current = group
  }, [roads, showRoads, cameraOffset])

  const gridLayerRef = useRef<L.LayerGroup | null>(null)
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    if (gridLayerRef.current) {
      map.removeLayer(gridLayerRef.current)
    }

    if (!showGrid) {
      gridLayerRef.current = null
      return
    }

    const group = L.layerGroup()
    const minorStep = 100
    const majorStep = 1000

    for (let x = 0; x <= canvasWidth; x += minorStep) {
      const isMajor = x % majorStep === 0
      const line = L.polyline(
        [gameCoordsToLatLng(x, 0, cameraOffset), gameCoordsToLatLng(x, canvasHeight, cameraOffset)],
        { color: 'rgba(255,255,255,' + (isMajor ? '0.35)' : '0.12)'), weight: isMajor ? 1.5 : 0.5, interactive: false },
      )
      group.addLayer(line)

      if (isMajor && x > 0) {
        const gridNum = String(Math.floor(x / 100)).padStart(3, '0')
        const marker = L.marker(gameCoordsToLatLng(x, 0, cameraOffset), {
          icon: L.divIcon({
            className: 'reforger-grid-label-x',
            html: `<span>${gridNum}</span>`,
            iconSize: [30, 14],
            iconAnchor: [15, -2],
          }),
          interactive: false,
        })
        group.addLayer(marker)
      }
    }

    for (let z = 0; z <= canvasHeight; z += minorStep) {
      const isMajor = z % majorStep === 0
      const line = L.polyline(
        [gameCoordsToLatLng(0, z, cameraOffset), gameCoordsToLatLng(canvasWidth, z, cameraOffset)],
        { color: 'rgba(255,255,255,' + (isMajor ? '0.35)' : '0.12)'), weight: isMajor ? 1.5 : 0.5, interactive: false },
      )
      group.addLayer(line)

      if (isMajor && z > 0) {
        const gridNum = String(Math.floor(z / 100)).padStart(3, '0')
        const marker = L.marker(gameCoordsToLatLng(0, z, cameraOffset), {
          icon: L.divIcon({
            className: 'reforger-grid-label-z',
            html: `<span>${gridNum}</span>`,
            iconSize: [30, 14],
            iconAnchor: [32, 7],
          }),
          interactive: false,
        })
        group.addLayer(marker)
      }
    }

    group.addTo(map)
    gridLayerRef.current = group
  }, [showGrid, canvasWidth, canvasHeight, cameraOffset])

  const handleZoomIn = useCallback(() => mapRef.current?.zoomIn(), [])
  const handleZoomOut = useCallback(() => mapRef.current?.zoomOut(), [])
  const handleFitBounds = useCallback(() => {
    mapRef.current?.fitBounds(bounds)
  }, [bounds])

  const handleThematicLayerToggle = useCallback((layerId: string, data: ThematicLayerData | null) => {
    const map = mapRef.current
    if (!map) return

    if (!data) {
      const existing = thematicLayersRef.current.get(layerId)
      if (existing) {
        map.removeLayer(existing)
        thematicLayersRef.current.delete(layerId)
      }
      return
    }

    const human = data.human
    if (!human) return

    // LOS: draw line between two points
    if (layerId === 'los' && human.from && human.to) {
      const existing = thematicLayersRef.current.get(layerId)
      if (existing) map.removeLayer(existing)

      const group = L.layerGroup()
      const from = gameCoordsToLatLng(human.from[0], human.from[1], cameraOffset)
      const to = gameCoordsToLatLng(human.to[0], human.to[1], cameraOffset)
      const lineColor = human.color || (human.visible ? '#00C853' : '#FF1744')

      const line = L.polyline([from, to], {
        color: lineColor,
        weight: 3,
        opacity: 0.9,
        dashArray: human.visible ? undefined : '8 6',
      })
      group.addLayer(line)

      L.circleMarker(from, { radius: 5, color: '#2196F3', fillColor: '#2196F3', fillOpacity: 1, weight: 1 }).addTo(group)
      L.circleMarker(to, { radius: 5, color: lineColor, fillColor: lineColor, fillOpacity: 1, weight: 1 }).addTo(group)

      if (human.obstruction) {
        const obs = human.obstruction
        const obsPos = gameCoordsToLatLng(obs.world_pos[0], obs.world_pos[1], cameraOffset)
        L.circleMarker(obsPos, { radius: 4, color: '#FF1744', fillColor: '#FF1744', fillOpacity: 0.8, weight: 1 })
          .bindTooltip(`Blocked at ${obs.distance_m}m`, { permanent: false })
          .addTo(group)
      }

      group.addTo(map)
      thematicLayersRef.current.set(layerId, group)
      return
    }

    // Viewshed: canvas image overlay + observer marker
    if (layerId === 'viewshed' && human.grid && human.origin) {
      const existing = thematicLayersRef.current.get(layerId)
      if (existing) map.removeLayer(existing)

      const group = L.layerGroup()
      const cellSize = human.grid_size_m || 100
      const [originX, originZ] = human.origin
      const rows = human.grid.length
      const cols = human.grid[0]?.length || 0

      if (rows > 0 && cols > 0) {
        const canvas = document.createElement('canvas')
        canvas.width = cols
        canvas.height = rows
        const ctx = canvas.getContext('2d')
        if (ctx) {
          const imgData = ctx.createImageData(cols, rows)
          const data = imgData.data
          for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
              const val = human.grid[r][c]
              const pixIdx = ((rows - 1 - r) * cols + c) * 4
              if (val === 1) {
                data[pixIdx] = 0; data[pixIdx + 1] = 200; data[pixIdx + 2] = 0; data[pixIdx + 3] = 90
              } else {
                data[pixIdx] = 200; data[pixIdx + 1] = 0; data[pixIdx + 2] = 0; data[pixIdx + 3] = 50
              }
            }
          }
          ctx.putImageData(imgData, 0, 0)

          const sw = gameCoordsToLatLng(originX, originZ, cameraOffset)
          const ne = gameCoordsToLatLng(originX + cols * cellSize, originZ + rows * cellSize, cameraOffset)
          const overlay = L.imageOverlay(canvas.toDataURL(), L.latLngBounds(sw, ne), { opacity: 1, interactive: false })
          group.addLayer(overlay)
        }
      }

      if (human.observer) {
        const obsPos = gameCoordsToLatLng(human.observer[0], human.observer[1], cameraOffset)
        L.circleMarker(obsPos, { radius: 6, color: '#FFD600', fillColor: '#FFD600', fillOpacity: 1, weight: 2 })
          .bindTooltip('Observer', { permanent: true, direction: 'top', offset: [0, -8] })
          .addTo(group)
      }

      group.addTo(map)
      thematicLayersRef.current.set(layerId, group)
      return
    }
  }, [cameraOffset])

  const handleInteractiveModeChange = useCallback((mode: InteractiveMode) => {
    setInteractiveMode(mode)
    interactiveModeRef.current = mode
    const map = mapRef.current
    if (map) {
      const container = map.getContainer()
      container.style.cursor = mode !== 'none' ? 'crosshair' : ''
    }
  }, [])

  const handleThematicOpacityChange = useCallback((layerId: string, opacity: number) => {
    thematicOpacityRef.current.set(layerId, opacity)
    const group = thematicLayersRef.current.get(layerId)
    if (!group) return
    group.eachLayer((layer) => {
      if ('setStyle' in layer && typeof (layer as L.Path).setStyle === 'function') {
        (layer as L.Path).setStyle({ fillOpacity: opacity })
      }
    })
  }, [])

  const tileLayersRef = useRef<Map<string, L.TileLayer>>(new Map())

  const handleTileLayerToggle = useCallback((layerId: string, urlTemplate: string | null) => {
    const map = mapRef.current
    if (!map) return

    const existing = tileLayersRef.current.get(layerId)
    if (existing) {
      map.removeLayer(existing)
      tileLayersRef.current.delete(layerId)
    }

    if (!urlTemplate) return

    const fullUrl = `${getBackendOrigin()}${urlTemplate}`

    const tileLayer = new InvertedYTileLayer(fullUrl, {
      opacity: thematicOpacityRef.current.get(layerId) ?? 0.6,
      maxZoom: tileMaxZoom,
      minZoom: tileMinZoom,
      zoomReverse: true,
      bounds,
      tileSize: TILE_SIZE,
      noWrap: true,
      crossOrigin: 'anonymous',
      updateWhenZooming: false,
      keepBuffer: 3,
    })
    tileLayer.addTo(map)
    tileLayersRef.current.set(layerId, tileLayer)
  }, [bounds, tileMaxZoom, tileMinZoom])

  const handleTileLayerOpacity = useCallback((layerId: string, opacity: number) => {
    const tileLayer = tileLayersRef.current.get(layerId)
    if (tileLayer) {
      tileLayer.setOpacity(opacity)
    }
    thematicOpacityRef.current.set(layerId, opacity)
  }, [])

  return (
    <div className="relative w-full h-full overflow-hidden">
      <div ref={containerRef} className="w-full h-full" style={{ background: '#1a2332' }} />

      {dataLayerVisibility && onDataLayerChange && onBaseMapChange ? (
        <LayerControlPanel
          mapId={mapId_forLayers || mapId}
          hasMilitaryTiles={hasMilitaryTiles}
          hasSatelliteTiles={hasSatelliteTiles}
          baseMapMode={baseMapMode}
          onBaseMapChange={onBaseMapChange}
          dataLayerVisibility={dataLayerVisibility}
          onDataLayerChange={onDataLayerChange}
          onThematicLayerToggle={handleThematicLayerToggle}
          onThematicOpacityChange={handleThematicOpacityChange}
          onTileLayerToggle={handleTileLayerToggle}
          onTileLayerOpacity={handleTileLayerOpacity}
          analysisTiles={analysisTiles}
          onInteractiveModeChange={handleInteractiveModeChange}
          interactiveClick={interactiveClick}
          hiddenLandmarkTypes={hiddenLandmarkTypes || new Set()}
          onToggleLandmarkType={onToggleLandmarkType || (() => {})}
          landmarkTypes={landmarkTypes || []}
          hiddenRoadTypes={hiddenRoadTypes || new Set()}
          onToggleRoadType={onToggleRoadType || (() => {})}
          roadTypes={roadTypes || []}
          hiddenZoneTypes={hiddenZoneTypes || new Set()}
          onToggleZoneType={onToggleZoneType || (() => {})}
          zoneTypes={zoneTypes || []}
        />
      ) : null}

      <div className="absolute top-14 right-3 z-[1000] flex flex-col gap-1">
        <Button variant="secondary" size="icon" className="h-8 w-8 shadow-md" onClick={handleZoomIn}>
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button variant="secondary" size="icon" className="h-8 w-8 shadow-md" onClick={handleZoomOut}>
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button variant="secondary" size="icon" className="h-8 w-8 shadow-md" onClick={handleFitBounds}>
          <Maximize className="h-4 w-4" />
        </Button>
      </div>

      <div className="absolute bottom-3 left-3 z-[1000] flex items-center gap-2">
        {cursorCoord && (
          <>
            <Badge variant="secondary" className="font-mono text-xs">
              <Crosshair className="h-3 w-3 mr-1" />
              {cursorCoord.grid}
            </Badge>
            <Badge variant="outline" className="font-mono text-xs bg-background/80">
              {cursorCoord.x}, {cursorCoord.z}
            </Badge>
            {cursorCoord.elev != null && (
              <Badge variant="outline" className="font-mono text-xs bg-background/80">
                <Mountain className="h-3 w-3 mr-1" />
                {cursorCoord.elev}m
              </Badge>
            )}
          </>
        )}
        <Badge variant="secondary" className="text-xs">
          LOD {MAX_ZOOM - currentZoom}
        </Badge>
      </div>

      <MapInfoCard mapId={mapId_forLayers || mapId} mapName={mapName} />

      <style jsx global>{`
        .reforger-tooltip {
          background: rgba(0,0,0,0.8);
          border: 1px solid rgba(255,255,255,0.2);
          color: white;
          font-size: 12px;
          padding: 2px 6px;
          border-radius: 3px;
        }
        .reforger-place-label {
          background: transparent;
          border: none;
          box-shadow: none;
          color: #fef9c3;
          font-size: 12px;
          font-weight: 500;
          text-shadow: 1px 1px 3px rgba(0,0,0,0.95), -1px -1px 2px rgba(0,0,0,0.7);
          padding: 0;
          white-space: nowrap;
        }
        .reforger-place-label::before {
          display: none;
        }
        .reforger-zone-label {
          background: transparent;
          border: none;
          box-shadow: none;
          color: white;
          font-size: 13px;
          font-weight: 500;
          text-shadow: 1px 1px 3px rgba(0,0,0,0.9);
        }
        .reforger-grid-label-x span,
        .reforger-grid-label-z span {
          color: rgba(255,255,255,0.55);
          font-size: 10px;
          font-family: monospace;
          text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
          white-space: nowrap;
        }
      `}</style>
    </div>
  )
}
