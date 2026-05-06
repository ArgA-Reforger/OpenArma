'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useI18n } from '@/lib/i18n'
import { getBackendOrigin } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Slider } from '@/components/ui/slider'
import {
  Play, Pause, SkipBack, SkipForward, ChevronsLeft, ChevronsRight,
  ArrowLeft, Eye, EyeOff, Users, Crosshair,
} from 'lucide-react'
import type { LandmarkData, ZoneData, RoadData } from '@/types/map'
import { ReforgerMapViewer } from '@/app/(user)/maps/reforger-map-viewer'
import type { BaseMapMode } from '@/app/(user)/maps/layer-control-panel'

// ─── Shared types ──────────────────────────────────────────────────

export interface ReplayMetadata {
  total_frames: number
  sessions: { start_frame: number; end_frame: number; start_time: string; end_time: string; frame_count: number }[]
}

export interface LightGroup {
  id: string; label: string; faction: string; control: string
  position: number[]; member_count: number; casualties: number
  current_waypoint_type: string; combat_mode: string
  speed_mode: string; formation: string
}

export interface LightUnit {
  entity_id: string; group_id: string; faction: string
  position: number[]; life_state: string; health: number
}

export interface KillEvent {
  type: 'kill'
  victim_id: string; victim_name: string; victim_faction: string
  killer_id: string; killer_name: string; killer_faction: string
  position: number[]
}

export interface FrameData {
  request_id: number; game_time: string; timestamp: number
  groups: LightGroup[]; units: LightUnit[]
  known_enemies: unknown[]; events: KillEvent[]
}

export interface ReplayMapData {
  id: number; name: string; size_x: number; size_z: number
  tile_min_zoom: number; tile_max_zoom: number
}

export interface ReplayTileInfo {
  has_military_tiles: boolean
  military_url_template: string
  military_zooms: number[]
  military_grid_size: number
  has_satellite_tiles: boolean
  tile_url_template: string
  overview_grid_size: number
  analysis_tiles?: Record<string, { ready: boolean; zooms: number[]; url_template: string }>
}

// ─── Props ─────────────────────────────────────────────────────────

export interface ReplayViewerProps {
  title: string
  metadata: ReplayMetadata
  mapData: ReplayMapData
  tileInfo: ReplayTileInfo | undefined
  frames: FrameData[]
  landmarks?: LandmarkData[]
  zones?: ZoneData[]
  roads?: RoadData[]
  onBack?: () => void
  onSessionChange?: (sessionIndex: number) => void
}

// ─── Helpers ───────────────────────────────────────────────────────

function gameCoordsToLatLng(x: number, z: number): L.LatLng {
  return L.latLng(z, x)
}

function lerp(a: number[], b: number[], t: number): number[] {
  return a.map((v, i) => v + (b[i] - v) * t)
}

const FACTION_COLORS: Record<string, string> = {
  US: '#3b82f6',
  USSR: '#ef4444',
  RHS_AFRF: '#ef4444',
  FIA: '#22c55e',
  CIV: '#a3a3a3',
}

const SPEED_MAP: Record<string, number> = { '0.5x': 2000, '1x': 1000, '2x': 500, '4x': 250, '8x': 125 }
const SPEED_LABELS = Object.keys(SPEED_MAP)

const GROUP_TYPE_MAP: Record<string, string> = { SQUAD: 'Squad', TEAM: 'Recon', SECTION: 'Section' }
function resolveGroupLabel(raw: string | undefined): string {
  if (!raw) return 'Unknown'
  if (!raw.startsWith('#')) return raw
  const m = raw.match(/_a(\w+?)_/)
  return (m?.[1] && GROUP_TYPE_MAP[m[1]]) || 'Squad'
}

// ─── Component ─────────────────────────────────────────────────────

export function ReplayViewer({
  title,
  metadata,
  mapData,
  tileInfo,
  frames,
  landmarks: externalLandmarks,
  zones: externalZones,
  roads: externalRoads,
  onBack,
  onSessionChange,
}: ReplayViewerProps) {
  const { t } = useI18n()

  const mapRef = useRef<L.Map | null>(null)
  const groupLayerRef = useRef<L.LayerGroup>(L.layerGroup())
  const unitLayerRef = useRef<L.LayerGroup>(L.layerGroup())
  const trailLayerRef = useRef<L.LayerGroup>(L.layerGroup())
  const eventLayerRef = useRef<L.LayerGroup>(L.layerGroup())

  const [frameIndex, setFrameIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speedLabel, setSpeedLabel] = useState('1x')
  const [showUnits, setShowUnits] = useState(true)
  const [showTrails, setShowTrails] = useState(true)
  const [showEvents, setShowEvents] = useState(true)
  const [selectedSession, setSelectedSession] = useState(0)
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null)
  const [baseMapMode, setBaseMapMode] = useState<BaseMapMode>('military')
  const [dataLayerVisibility, setDataLayerVisibility] = useState({
    landmarks: false, roads: false, zones: false, grid: true,
  })

  const animRef = useRef<number>(0)
  const frameStartRef = useRef(0)
  const playingRef = useRef(false)
  const frameIndexRef = useRef(0)
  const speedRef = useRef(SPEED_MAP['1x'])

  useEffect(() => { playingRef.current = playing }, [playing])
  useEffect(() => { frameIndexRef.current = frameIndex }, [frameIndex])
  useEffect(() => { speedRef.current = SPEED_MAP[speedLabel] }, [speedLabel])

  // Reset frame index when frames change (session switch)
  useEffect(() => { setFrameIndex(0) }, [frames])

  const hasMilitary = !!tileInfo?.has_military_tiles && !!tileInfo?.military_url_template
  const hasSatellite = !!tileInfo?.has_satellite_tiles || !!tileInfo?.tile_url_template

  const effectiveBase = baseMapMode === 'satellite' && hasSatellite ? 'satellite' : hasMilitary ? 'military' : 'satellite'

  const tileUrl = useMemo(() => {
    if (effectiveBase === 'military' && tileInfo?.military_url_template)
      return `${getBackendOrigin()}${tileInfo.military_url_template}`
    if (tileInfo?.tile_url_template)
      return `${getBackendOrigin()}${tileInfo.tile_url_template}`
    return undefined
  }, [tileInfo, effectiveBase])

  const satelliteOverlayUrl = useMemo(() => {
    if (effectiveBase === 'military' && hasSatellite && tileInfo?.tile_url_template)
      return `${getBackendOrigin()}${tileInfo.tile_url_template}`
    return undefined
  }, [effectiveBase, hasSatellite, tileInfo])

  const handleDataLayerChange = useCallback((layer: keyof typeof dataLayerVisibility, visible: boolean) => {
    setDataLayerVisibility(prev => ({ ...prev, [layer]: visible }))
  }, [])

  const [hiddenLandmarkTypes, setHiddenLandmarkTypes] = useState<Set<string>>(new Set())
  const [hiddenRoadTypes, setHiddenRoadTypes] = useState<Set<string>>(new Set())
  const [hiddenZoneTypes, setHiddenZoneTypes] = useState<Set<string>>(new Set())

  const filteredLandmarks = useMemo(() => {
    if (!dataLayerVisibility.landmarks) return []
    return (externalLandmarks || []).filter(lm => !hiddenLandmarkTypes.has(lm.type))
  }, [externalLandmarks, hiddenLandmarkTypes, dataLayerVisibility.landmarks])

  const filteredZones = useMemo(() => {
    if (!dataLayerVisibility.zones) return []
    return (externalZones || []).filter(z => !hiddenZoneTypes.has(z.type))
  }, [externalZones, hiddenZoneTypes, dataLayerVisibility.zones])

  const filteredRoads = useMemo(() => {
    if (!dataLayerVisibility.roads) return []
    return (externalRoads || []).filter(r => !hiddenRoadTypes.has(r.type))
  }, [externalRoads, hiddenRoadTypes, dataLayerVisibility.roads])

  const landmarkTypes = useMemo(() => {
    const counts = new Map<string, number>()
    ;(externalLandmarks || []).forEach(lm => counts.set(lm.type, (counts.get(lm.type) || 0) + 1))
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]) as [string, number][]
  }, [externalLandmarks])

  const roadTypes = useMemo(() => {
    const counts = new Map<string, number>()
    ;(externalRoads || []).forEach(r => counts.set(r.type, (counts.get(r.type) || 0) + 1))
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]) as [string, number][]
  }, [externalRoads])

  const zoneTypes = useMemo(() => {
    const counts = new Map<string, number>()
    ;(externalZones || []).forEach(z => counts.set(z.type, (counts.get(z.type) || 0) + 1))
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]) as [string, number][]
  }, [externalZones])

  const toggleType = useCallback((setter: React.Dispatch<React.SetStateAction<Set<string>>>) => (type: string) => {
    setter(prev => { const next = new Set(prev); next.has(type) ? next.delete(type) : next.add(type); return next })
  }, [])

  const handleMapReady = useCallback((map: L.Map) => {
    mapRef.current = map
    groupLayerRef.current.addTo(map)
    unitLayerRef.current.addTo(map)
    trailLayerRef.current.addTo(map)
    eventLayerRef.current.addTo(map)
  }, [])

  const handleMapDestroy = useCallback(() => {
    mapRef.current = null
  }, [])

  const currentFrame = frames[frameIndex]
  const nextFrame = frames[frameIndex + 1]

  const renderFrame = useCallback((frame: FrameData, nextF: FrameData | undefined, t_interp: number) => {
    if (!mapRef.current) return
    groupLayerRef.current.clearLayers()
    unitLayerRef.current.clearLayers()
    eventLayerRef.current.clearLayers()

    for (const u of frame.units) {
      const pos = nextF
        ? lerp(u.position, nextF.units.find(nu => nu.entity_id === u.entity_id)?.position || u.position, t_interp)
        : u.position
      const latlng = gameCoordsToLatLng(pos[0], pos[2])
      const color = FACTION_COLORS[u.faction] || '#6b7280'
      const dead = u.life_state !== 'alive'
      const incap = u.life_state === 'incapacitated'

      if (dead && !incap) {
        const xIcon = L.divIcon({
          className: 'replay-dead',
          html: `<span style="color:${color};font-size:8px;opacity:0.5;font-weight:bold;">✕</span>`,
          iconSize: [10, 10],
          iconAnchor: [5, 5],
        })
        L.marker(latlng, { icon: xIcon, interactive: false }).addTo(unitLayerRef.current)
      } else {
        const marker = L.circleMarker(latlng, {
          radius: incap ? 3 : 4,
          fillColor: incap ? '#fbbf24' : color,
          color: incap ? '#f59e0b' : color,
          weight: 1,
          fillOpacity: incap ? 0.6 : 0.85,
        })
        const group = frame.groups.find(g => g.id === u.group_id)
        const label = group ? resolveGroupLabel(group.label) : u.faction
        marker.bindTooltip(
          `<b>${label}</b> · ${u.faction}<br/>HP: ${Math.round((u.health ?? 1) * 100)}% · ${u.life_state}`,
          { permanent: false, direction: 'top', offset: [0, -6] }
        )
        marker.addTo(unitLayerRef.current)
      }
    }

    if (showUnits) {
      for (const g of frame.groups) {
        const pos = nextF
          ? lerp(g.position, nextF.groups.find(ng => ng.id === g.id)?.position || g.position, t_interp)
          : g.position
        const latlng = gameCoordsToLatLng(pos[0], pos[2])
        const color = FACTION_COLORS[g.faction] || '#6b7280'
        const isSelected = selectedGroup === g.id
        const label = resolveGroupLabel(g.label)

        if (isSelected) {
          L.circleMarker(latlng, {
            radius: 14,
            fillColor: 'transparent',
            color: '#ffffff',
            weight: 2,
            fillOpacity: 0,
            dashArray: '3 3',
          }).addTo(groupLayerRef.current)
        }

        const textIcon = L.divIcon({
          className: 'replay-label',
          html: `<span style="color:${color};font-size:9px;font-weight:600;text-shadow:0 0 3px #000,0 0 3px #000;white-space:nowrap;">${label}</span>`,
          iconAnchor: [0, -10],
        })
        const labelMarker = L.marker(latlng, { icon: textIcon, interactive: true })
        labelMarker.on('click', () => setSelectedGroup(g.id === selectedGroup ? null : g.id))
        labelMarker.bindTooltip(
          `<b>${label}</b><br/>${g.member_count - g.casualties}/${g.member_count} · ${g.current_waypoint_type}<br/>${g.combat_mode} · ${g.formation}`,
          { permanent: false, direction: 'top', offset: [0, -14] }
        )
        labelMarker.addTo(groupLayerRef.current)
      }
    }

    if (showEvents && frame.events) {
      for (const evt of frame.events) {
        if (evt.type !== 'kill' || !evt.position) continue
        const latlng = gameCoordsToLatLng(evt.position[0], evt.position[2])
        const skullIcon = L.divIcon({
          className: 'replay-kill',
          html: '<span style="font-size:12px;filter:drop-shadow(0 0 2px #000);">💀</span>',
          iconSize: [14, 14],
          iconAnchor: [7, 7],
        })
        const killMarker = L.marker(latlng, { icon: skullIcon, interactive: true })
        killMarker.bindTooltip(
          `<b>${evt.killer_name}</b> (${evt.killer_faction})<br/>→ ${evt.victim_name} (${evt.victim_faction})`,
          { permanent: false, direction: 'top', offset: [0, -10] }
        )
        killMarker.addTo(eventLayerRef.current)
      }
    }
  }, [showUnits, showEvents, selectedGroup])

  const renderTrails = useCallback(() => {
    trailLayerRef.current.clearLayers()
    if (!showTrails || frames.length < 2) return
    const trailFrames = frames.slice(0, frameIndex + 1)
    const groupIds = new Set(trailFrames[0]?.groups.map(g => g.id) || [])

    for (const gid of groupIds) {
      const pts: L.LatLng[] = []
      for (const f of trailFrames) {
        const g = f.groups.find(gr => gr.id === gid)
        if (g) pts.push(gameCoordsToLatLng(g.position[0], g.position[2]))
      }
      if (pts.length < 2) continue
      const color = FACTION_COLORS[trailFrames[0].groups.find(g => g.id === gid)?.faction || ''] || '#6b7280'
      L.polyline(pts, { color, weight: 2, opacity: 0.5, dashArray: '4 4' }).addTo(trailLayerRef.current)
    }
  }, [frames, frameIndex, showTrails])

  useEffect(() => { renderTrails() }, [renderTrails])
  useEffect(() => {
    if (currentFrame) renderFrame(currentFrame, nextFrame, 0)
  }, [frameIndex, currentFrame, nextFrame, renderFrame])

  useEffect(() => {
    if (!playing) {
      cancelAnimationFrame(animRef.current)
      return
    }
    frameStartRef.current = performance.now()

    const tick = (now: number) => {
      if (!playingRef.current) return
      const elapsed = now - frameStartRef.current
      const speed = speedRef.current
      const t_interp = Math.min(elapsed / speed, 1)

      const fi = frameIndexRef.current
      const curF = frames[fi]
      const nxtF = frames[fi + 1]
      if (curF) renderFrame(curF, nxtF, t_interp)

      if (elapsed >= speed) {
        if (fi < frames.length - 1) {
          const next = fi + 1
          setFrameIndex(next)
          frameIndexRef.current = next
          frameStartRef.current = now
        } else {
          setPlaying(false)
          return
        }
      }
      animRef.current = requestAnimationFrame(tick)
    }
    animRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(animRef.current)
  }, [playing, frames, renderFrame])

  const groupStats = useMemo(() => {
    if (!currentFrame) return []
    return currentFrame.groups.map(g => {
      const alive = currentFrame.units.filter(u => u.group_id === g.id && u.life_state === 'alive').length
      const total = currentFrame.units.filter(u => u.group_id === g.id).length
      return { ...g, alive, total }
    })
  }, [currentFrame])

  const factionStats = useMemo(() => {
    if (!currentFrame) return new Map<string, { alive: number; total: number; groups: number }>()
    const stats = new Map<string, { alive: number; total: number; groups: number }>()
    for (const g of currentFrame.groups) {
      const f = g.faction
      const prev = stats.get(f) || { alive: 0, total: 0, groups: 0 }
      const gAlive = currentFrame.units.filter(u => u.group_id === g.id && u.life_state === 'alive').length
      const gTotal = currentFrame.units.filter(u => u.group_id === g.id).length
      stats.set(f, { alive: prev.alive + gAlive, total: prev.total + gTotal, groups: prev.groups + 1 })
    }
    return stats
  }, [currentFrame])

  const totalAlive = useMemo(() => {
    if (!currentFrame) return 0
    return currentFrame.units.filter(u => u.life_state === 'alive').length
  }, [currentFrame])

  const killLog = useMemo(() => {
    if (!frames.length) return []
    const kills: KillEvent[] = []
    for (let i = 0; i <= frameIndex; i++) {
      for (const evt of frames[i].events || []) {
        if (evt.type === 'kill') kills.push(evt)
      }
    }
    return kills.slice(-20)
  }, [frames, frameIndex])

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-2 border-b bg-background/80 backdrop-blur-sm shrink-0">
        {onBack && (
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
        )}
        <div className="flex-1 min-w-0">
          <h2 className="text-sm font-semibold truncate">{title} — {t('replay.title')}</h2>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {metadata.sessions.length > 1 && (
              <select
                className="bg-transparent border rounded px-1 py-0.5 text-xs"
                value={selectedSession}
                onChange={e => {
                  const idx = Number(e.target.value)
                  setSelectedSession(idx)
                  setPlaying(false)
                  onSessionChange?.(idx)
                }}
              >
                {metadata.sessions.map((s, i) => (
                  <option key={i} value={i}>
                    {t('replay.session')} {i + 1}: {s.start_time} ~ {s.end_time} ({s.frame_count} {t('replay.frames')})
                  </option>
                ))}
              </select>
            )}
            <span>{currentFrame?.game_time || '--:--'}</span>
            <span>·</span>
            <span>{t('replay.frame')} {frameIndex + 1}/{frames.length}</span>
            <span>·</span>
            <span><Users className="h-3 w-3 inline" /> {totalAlive}</span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant={showUnits ? 'secondary' : 'ghost'}
            size="icon" className="h-7 w-7"
            onClick={() => setShowUnits(!showUnits)}
            title="Toggle squad labels"
          >
            <Users className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant={showTrails ? 'secondary' : 'ghost'}
            size="icon" className="h-7 w-7"
            onClick={() => setShowTrails(!showTrails)}
            title="Toggle trails"
          >
            {showTrails ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
          </Button>
          <Button
            variant={showEvents ? 'secondary' : 'ghost'}
            size="icon" className="h-7 w-7"
            onClick={() => setShowEvents(!showEvents)}
            title="Toggle kill events"
          >
            <Crosshair className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Main area */}
      <div className="flex-1 flex min-h-0">
        {/* Map */}
        <div className="flex-1 relative min-w-0">
          {tileUrl ? (
            <ReforgerMapViewer
              mapId={mapData.id}
              mapName={mapData.name}
              canvasWidth={mapData.size_x}
              canvasHeight={mapData.size_z}
              tileUrlTemplate={tileUrl}
              tileMinZoom={mapData.tile_min_zoom}
              tileMaxZoom={mapData.tile_max_zoom}
              overviewGridSize={effectiveBase === 'military' ? (tileInfo?.military_grid_size || 1) : (tileInfo?.overview_grid_size || 1)}
              satelliteTileUrl={satelliteOverlayUrl}
              landmarks={filteredLandmarks}
              zones={filteredZones}
              roads={filteredRoads}
              showGrid={dataLayerVisibility.grid}
              showLandmarks={dataLayerVisibility.landmarks}
              showZones={dataLayerVisibility.zones}
              showRoads={dataLayerVisibility.roads}
              mapId_forLayers={mapData.id}
              hasMilitaryTiles={hasMilitary}
              hasSatelliteTiles={hasSatellite}
              baseMapMode={effectiveBase as BaseMapMode}
              onBaseMapChange={setBaseMapMode}
              dataLayerVisibility={dataLayerVisibility}
              onDataLayerChange={handleDataLayerChange}
              hiddenLandmarkTypes={hiddenLandmarkTypes}
              onToggleLandmarkType={toggleType(setHiddenLandmarkTypes)}
              landmarkTypes={landmarkTypes}
              hiddenRoadTypes={hiddenRoadTypes}
              onToggleRoadType={toggleType(setHiddenRoadTypes)}
              roadTypes={roadTypes}
              hiddenZoneTypes={hiddenZoneTypes}
              onToggleZoneType={toggleType(setHiddenZoneTypes)}
              zoneTypes={zoneTypes}
              analysisTiles={tileInfo?.analysis_tiles}
              onMapReady={handleMapReady}
              onMapDestroy={handleMapDestroy}
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center bg-muted/20">
              <p className="text-sm text-muted-foreground">No map tiles available</p>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="w-72 border-l bg-background/80 backdrop-blur-sm overflow-y-auto">
          <div className="p-3 space-y-3">
            {/* Faction overview */}
            <div className="space-y-1">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Factions</h3>
              {[...factionStats.entries()].map(([faction, st]) => (
                <div key={faction} className="flex items-center gap-2 text-xs px-1">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: FACTION_COLORS[faction] || '#6b7280' }} />
                  <span className="font-medium">{faction}</span>
                  <span className="text-muted-foreground ml-auto">{st.alive}/{st.total} alive · {st.groups} squads</span>
                </div>
              ))}
            </div>

            {/* Groups */}
            <div className="space-y-1">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {t('replay.squads')} ({groupStats.length})
              </h3>
              {groupStats.map(g => {
                const color = FACTION_COLORS[g.faction] || '#6b7280'
                const label = resolveGroupLabel(g.label)
                const isSelected = selectedGroup === g.id
                return (
                  <div
                    key={g.id}
                    className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors text-xs ${
                      isSelected ? 'bg-accent' : 'hover:bg-muted/50'
                    }`}
                    onClick={() => {
                      setSelectedGroup(g.id === selectedGroup ? null : g.id)
                      const pos = g.position
                      if (mapRef.current && pos) {
                        mapRef.current.panTo(gameCoordsToLatLng(pos[0], pos[2]))
                      }
                    }}
                  >
                    <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: color }} />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{label}</div>
                      <div className="text-muted-foreground">{g.alive}/{g.total} · {g.current_waypoint_type}</div>
                    </div>
                    <Badge variant="outline" className="text-[9px] px-1 py-0 uppercase">
                      {g.combat_mode === 'hold_fire' ? 'HF' : 'FAW'}
                    </Badge>
                  </div>
                )
              })}
            </div>

            {/* Kill log */}
            {killLog.length > 0 && (
              <div className="space-y-1">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Kill Log ({killLog.length})
                </h3>
                <div className="space-y-0.5 max-h-40 overflow-y-auto">
                  {killLog.slice().reverse().map((k, i) => (
                    <div key={i} className="text-[10px] text-muted-foreground leading-tight px-1">
                      <span style={{ color: FACTION_COLORS[k.killer_faction] || '#6b7280' }}>{k.killer_name}</span>
                      {' → '}
                      <span style={{ color: FACTION_COLORS[k.victim_faction] || '#6b7280' }}>{k.victim_name}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="border-t bg-background/80 backdrop-blur-sm px-4 py-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => { setFrameIndex(0); setPlaying(false) }}>
              <ChevronsLeft className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7"
              onClick={() => { setFrameIndex(Math.max(0, frameIndex - 1)); setPlaying(false) }}>
              <SkipBack className="h-4 w-4" />
            </Button>
            <Button
              variant={playing ? 'secondary' : 'default'}
              size="icon" className="h-8 w-8"
              onClick={() => {
                if (frameIndex >= frames.length - 1) {
                  setFrameIndex(0)
                  frameIndexRef.current = 0
                }
                setPlaying(!playing)
              }}
            >
              {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7"
              onClick={() => { setFrameIndex(Math.min(frames.length - 1, frameIndex + 1)); setPlaying(false) }}>
              <SkipForward className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7"
              onClick={() => { setFrameIndex(frames.length - 1); setPlaying(false) }}>
              <ChevronsRight className="h-4 w-4" />
            </Button>
          </div>

          <div className="flex-1">
            <Slider
              value={[frameIndex]}
              min={0}
              max={frames.length - 1}
              step={1}
              onValueChange={([v]) => { setFrameIndex(v); setPlaying(false) }}
            />
          </div>

          <div className="flex items-center gap-1">
            {SPEED_LABELS.map(s => (
              <Button
                key={s}
                variant={speedLabel === s ? 'secondary' : 'ghost'}
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setSpeedLabel(s)}
              >
                {s}
              </Button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
