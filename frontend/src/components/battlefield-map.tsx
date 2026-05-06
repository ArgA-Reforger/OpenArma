'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ZoomIn, ZoomOut, Crosshair, MapPin, Shield, AlertTriangle } from 'lucide-react'
import { useI18n } from '@/lib/i18n'
import { LANDMARK_CHIP_COLORS } from '@/lib/map-constants'

interface Position {
  x: number
  z: number
  y?: number
}

interface MapSquad {
  id: string
  name: string
  position: Position
  role?: string
  memberCount?: number
  casualties?: number
  combatMode?: string
}

interface MapEnemy {
  position: Position
  distance?: number
  time_since_endangered?: number
  time_since_side_recognized?: number
  unit_type?: string
  perceived_faction?: string
  identified?: boolean
  endangering?: boolean
  spottedBy?: string
}

interface MapLandmark {
  name: string
  type: string
  position: Position
}

interface BattlefieldMapProps {
  mapName?: string
  mapSizeX: number
  mapSizeZ: number
  imageUrl?: string
  squads?: MapSquad[]
  enemies?: MapEnemy[]
  landmarks?: MapLandmark[]
}

export function BattlefieldMap({
  mapName,
  mapSizeX,
  mapSizeZ,
  imageUrl,
  squads = [],
  enemies = [],
  landmarks = [],
}: BattlefieldMapProps) {
  const { t } = useI18n()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [zoom, setZoom] = useState(1)
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [hoveredSquad, setHoveredSquad] = useState<MapSquad | null>(null)
  const [canvasSize, setCanvasSize] = useState({ w: 600, h: 600 })
  const imgRef = useRef<HTMLImageElement | null>(null)

  useEffect(() => {
    if (!imageUrl) return
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.src = imageUrl
    img.onload = () => {
      imgRef.current = img
      draw()
    }
  }, [imageUrl])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const observer = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect
      const h = Math.min(width, 600)
      setCanvasSize({ w: width, h })
    })
    observer.observe(container)
    return () => observer.disconnect()
  }, [])

  const worldToCanvas = useCallback(
    (wx: number, wz: number) => {
      const scaleX = canvasSize.w / mapSizeX
      const scaleZ = canvasSize.h / mapSizeZ
      const scale = Math.min(scaleX, scaleZ) * zoom
      const cx = (wx / mapSizeX) * canvasSize.w * zoom + panOffset.x
      const cy = ((mapSizeZ - wz) / mapSizeZ) * canvasSize.h * zoom + panOffset.y
      return { x: cx, y: cy }
    },
    [canvasSize, mapSizeX, mapSizeZ, zoom, panOffset],
  )

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = canvasSize.w
    canvas.height = canvasSize.h

    ctx.fillStyle = '#1a1a2e'
    ctx.fillRect(0, 0, canvasSize.w, canvasSize.h)

    if (imgRef.current) {
      ctx.save()
      ctx.translate(panOffset.x, panOffset.y)
      ctx.scale(zoom, zoom)
      ctx.drawImage(imgRef.current, 0, 0, canvasSize.w, canvasSize.h)
      ctx.restore()
    } else {
      ctx.save()
      ctx.strokeStyle = '#2a2a4e'
      ctx.lineWidth = 0.5
      const gridStep = 1000
      for (let x = 0; x <= mapSizeX; x += gridStep) {
        const p = worldToCanvas(x, 0)
        const p2 = worldToCanvas(x, mapSizeZ)
        ctx.beginPath()
        ctx.moveTo(p.x, p.y)
        ctx.lineTo(p2.x, p2.y)
        ctx.stroke()
      }
      for (let z = 0; z <= mapSizeZ; z += gridStep) {
        const p = worldToCanvas(0, z)
        const p2 = worldToCanvas(mapSizeX, z)
        ctx.beginPath()
        ctx.moveTo(p.x, p.y)
        ctx.lineTo(p2.x, p2.y)
        ctx.stroke()
      }
      ctx.restore()
    }

    const minLandmarkZoom = 0.5
    if (zoom >= minLandmarkZoom) {
      for (const lm of landmarks) {
        const p = worldToCanvas(lm.position.x, lm.position.z)
        if (p.x < -20 || p.x > canvasSize.w + 20 || p.y < -20 || p.y > canvasSize.h + 20) continue
        const color = LANDMARK_CHIP_COLORS[lm.type] || '#94a3b8'
        ctx.fillStyle = color
        ctx.beginPath()
        ctx.arc(p.x, p.y, 3, 0, Math.PI * 2)
        ctx.fill()
        if (zoom >= 1) {
          ctx.font = '10px sans-serif'
          ctx.fillStyle = color
          ctx.fillText(lm.name, p.x + 5, p.y + 3)
        }
      }
    }

    for (const enemy of enemies) {
      const p = worldToCanvas(enemy.position.x, enemy.position.z)
      if (p.x < -20 || p.x > canvasSize.w + 20 || p.y < -20 || p.y > canvasSize.h + 20) continue
      const isEndangering = enemy.time_since_endangered != null ? enemy.time_since_endangered < 10 : enemy.endangering
      ctx.fillStyle = isEndangering ? '#ef4444' : '#f97316'
      ctx.beginPath()
      const sz = 5
      ctx.moveTo(p.x, p.y - sz)
      ctx.lineTo(p.x + sz, p.y + sz)
      ctx.lineTo(p.x - sz, p.y + sz)
      ctx.closePath()
      ctx.fill()
    }

    for (const squad of squads) {
      const p = worldToCanvas(squad.position.x, squad.position.z)
      if (p.x < -20 || p.x > canvasSize.w + 20 || p.y < -20 || p.y > canvasSize.h + 20) continue
      const isHovered = hoveredSquad?.id === squad.id
      ctx.fillStyle = isHovered ? '#60a5fa' : '#3b82f6'
      ctx.strokeStyle = '#ffffff'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.arc(p.x, p.y, isHovered ? 8 : 6, 0, Math.PI * 2)
      ctx.fill()
      ctx.stroke()
      ctx.font = 'bold 11px sans-serif'
      ctx.fillStyle = '#ffffff'
      ctx.textAlign = 'center'
      ctx.fillText(squad.name, p.x, p.y - 10)
      ctx.textAlign = 'start'
    }
  }, [canvasSize, zoom, panOffset, squads, enemies, landmarks, hoveredSquad, worldToCanvas])

  useEffect(() => {
    draw()
  }, [draw])

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true)
    setDragStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y })
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPanOffset({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y })
    }
  }

  const handleMouseUp = () => setIsDragging(false)

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.1 : 0.1
    setZoom((z) => Math.max(0.3, Math.min(5, z + delta)))
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Crosshair className="h-5 w-5" />
            {t('armaChat.battlefieldMap')}
            {mapName && <Badge variant="outline">{mapName}</Badge>}
          </CardTitle>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setZoom((z) => Math.min(5, z + 0.3))}>
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setZoom((z) => Math.max(0.3, z - 0.3))}>
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => {
                setZoom(1)
                setPanOffset({ x: 0, y: 0 })
              }}
            >
              <MapPin className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-2">
        <div ref={containerRef} className="relative w-full overflow-hidden rounded-md border bg-muted">
          <canvas
            ref={canvasRef}
            style={{ width: '100%', height: canvasSize.h, cursor: isDragging ? 'grabbing' : 'grab' }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
          />
          {/* Legend */}
          <div className="absolute bottom-2 left-2 flex gap-2 text-[10px]">
            <span className="flex items-center gap-1">
              <Shield className="h-3 w-3 text-blue-500" /> {t('armaChat.friendlySquads')}
            </span>
            <span className="flex items-center gap-1">
              <AlertTriangle className="h-3 w-3 text-red-500" /> {t('armaChat.enemies')}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
