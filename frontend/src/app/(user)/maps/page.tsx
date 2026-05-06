'use client'

import { useRef, useState, useMemo, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  Collapsible, CollapsibleContent, CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import { useApi } from '@/hooks/use-api'
import { getBackendOrigin } from '@/lib/api'
import { useI18n } from '@/lib/i18n'
import { useAuthStore } from '@/stores/auth'
import { CardLoadingState } from '@/components/loading-state'
import {
  Upload, Trash2, Globe, MapPin, FileJson, Route,
  Plus, CircleDot, Layers, Eye, EyeOff, Image, Hexagon,
  ChevronUp, ChevronDown, ChevronRight, Search, MoreHorizontal,
  FolderPlus, Map as MapIcon, PanelRightClose, PanelRightOpen, Satellite, Landmark,
} from 'lucide-react'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import dynamic from 'next/dynamic'
import type { GameMap, MapLayer, LandmarkData, ZoneData, RoadData } from '@/types/map'
import { LANDMARK_CHIP_COLORS, ZONE_CHIP_COLORS, ROAD_CHIP_COLORS, getLandmarkDisplayName } from '@/lib/map-constants'
import { MapSelector } from './map-selector'
import type { BaseMapMode } from './layer-control-panel'

const ReforgerMapViewer = dynamic(
  () => import('./reforger-map-viewer').then((m) => m.ReforgerMapViewer),
  { ssr: false, loading: () => <div className="w-full h-full bg-muted animate-pulse" /> }
)

// ─── Collapsible Section Helper ────────────────────────────────────────────────

function PanelSection({
  title, icon, count, children, defaultOpen = false,
}: {
  title: string; icon: React.ReactNode; count?: number; children: React.ReactNode; defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex items-center justify-between w-full px-3 py-2 hover:bg-muted/50 rounded-md transition-colors text-sm font-medium">
        <div className="flex items-center gap-2">
          {icon}
          <span>{title}</span>
          {count !== undefined && <Badge variant="secondary" className="h-4 px-1 text-[10px]">{count}</Badge>}
        </div>
        <ChevronRight className={`h-3.5 w-3.5 text-muted-foreground transition-transform ${open ? 'rotate-90' : ''}`} />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="px-3 pb-3 pt-1">{children}</div>
      </CollapsibleContent>
    </Collapsible>
  )
}

// ─── Tile Progress Bar ────────────────────────────────────────────────────────

function TileProgressBar({ label, done, total, compact }: { label: string; done: number; total: number; compact?: boolean }) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0
  return (
    <div className={compact ? 'pl-3' : ''}>
      <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
        <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-[9px] text-muted-foreground mt-0.5">
        {compact ? `${done}/${total}` : `${label}: ${done}/${total} tiles (${pct}%)`}
      </p>
    </div>
  )
}

// ─── Compact Layer Row ─────────────────────────────────────────────────────────

function LayerRow({ layer, mapId, t, isFirst, isLast, onMoveUp, onMoveDown }: {
  layer: MapLayer; mapId: number; t: (k: string) => string
  isFirst: boolean; isLast: boolean; onMoveUp: () => void; onMoveDown: () => void
}) {
  const api = useApi()
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [localOpacity, setLocalOpacity] = useState(layer.opacity)

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/maps/admin/maps/${mapId}/layers/${layer.id}`),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['map-layers', mapId] }); toast.success(t('mapAdmin.layerDeleted')) },
    onError: (err: Error) => toast.error(err.message),
  })
  const toggleVisibility = useMutation({
    mutationFn: () => api.put(`/maps/admin/maps/${mapId}/layers/${layer.id}`, { visible: !layer.visible }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['map-layers', mapId] }),
  })
  const updateOpacity = useMutation({
    mutationFn: (opacity: number) => api.put(`/maps/admin/maps/${mapId}/layers/${layer.id}`, { opacity }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['map-layers', mapId] }),
  })
  const uploadMutation = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData(); fd.append('file', file)
      return api.upload(`/maps/admin/maps/${mapId}/layers/${layer.id}/image`, fd)
    },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['map-layers', mapId] }); toast.success(t('mapAdmin.imageUploaded')) },
    onError: (err: Error) => toast.error(err.message),
  })

  return (
    <div className="flex items-center gap-2 py-1.5 group">
      <div className="w-6 h-6 rounded bg-muted flex items-center justify-center shrink-0">
        {layer.image_path ? <Image className="h-3 w-3 text-primary" /> : <Layers className="h-3 w-3 text-muted-foreground" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1">
          <span className="text-xs font-medium truncate">{layer.name}</span>
          <Badge variant="outline" className="text-[9px] h-3.5 px-1">{layer.layer_type}</Badge>
        </div>
      </div>
      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
        <Button variant="ghost" size="icon" className="h-5 w-5" disabled={isFirst} onClick={onMoveUp}><ChevronUp className="h-3 w-3" /></Button>
        <Button variant="ghost" size="icon" className="h-5 w-5" disabled={isLast} onClick={onMoveDown}><ChevronDown className="h-3 w-3" /></Button>
        <Button variant="ghost" size="icon" className="h-5 w-5" onClick={() => toggleVisibility.mutate()}>
          {layer.visible ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3 text-muted-foreground" />}
        </Button>
        <input ref={fileRef} type="file" accept="image/*,.tga" className="hidden" onChange={(e) => {
          const file = e.target.files?.[0]; if (file) uploadMutation.mutate(file); e.target.value = ''
        }} />
        <Button variant="ghost" size="icon" className="h-5 w-5" onClick={() => fileRef.current?.click()}><Upload className="h-3 w-3" /></Button>
        <AlertDialog>
          <AlertDialogTrigger asChild><Button variant="ghost" size="icon" className="h-5 w-5 text-destructive"><Trash2 className="h-3 w-3" /></Button></AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader><AlertDialogTitle>{t('common.confirmDelete')}</AlertDialogTitle><AlertDialogDescription>{t('mapAdmin.confirmDeleteLayer')}</AlertDialogDescription></AlertDialogHeader>
            <AlertDialogFooter><AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel><AlertDialogAction onClick={() => deleteMutation.mutate()}>{t('common.delete')}</AlertDialogAction></AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
      <div className="w-12 flex items-center gap-0.5 shrink-0">
        <input type="range" min={0} max={1} step={0.05} value={localOpacity} className="w-10 h-3 accent-primary cursor-pointer"
          onChange={(e) => setLocalOpacity(parseFloat(e.target.value))} onMouseUp={() => updateOpacity.mutate(localOpacity)} />
      </div>
    </div>
  )
}

// ─── Data Rows ─────────────────────────────────────────────────────────────────

function LandmarkRow({ lm, mapId, onDeleted, t, locale }: { lm: LandmarkData; mapId: number; onDeleted: () => void; t: (k: string) => string; locale: string }) {
  const api = useApi()
  const del = useMutation({ mutationFn: () => api.delete(`/maps/admin/maps/${mapId}/landmarks/${lm.id}`), onSuccess: () => { onDeleted(); toast.success(t('mapAdmin.deleted')) }, onError: (e: Error) => toast.error(e.message) })
  return (
    <div className="flex items-center gap-2 py-1 group text-xs">
      <MapPin className="h-3 w-3 text-red-400 shrink-0" />
      <span className="flex-1 truncate">{getLandmarkDisplayName(lm, locale)}</span>
      <span className="text-muted-foreground font-mono text-[10px]">{Math.round(lm.position_x)},{Math.round(lm.position_z)}</span>
      <Button variant="ghost" size="icon" className="h-4 w-4 opacity-0 group-hover:opacity-100 text-destructive" onClick={() => del.mutate()}><Trash2 className="h-2.5 w-2.5" /></Button>
    </div>
  )
}

function ZoneRow({ zone, mapId, onDeleted, t }: { zone: ZoneData; mapId: number; onDeleted: () => void; t: (k: string) => string }) {
  const api = useApi()
  const del = useMutation({ mutationFn: () => api.delete(`/maps/admin/maps/${mapId}/zones/${zone.id}`), onSuccess: () => { onDeleted(); toast.success(t('mapAdmin.deleted')) }, onError: (e: Error) => toast.error(e.message) })
  return (
    <div className="flex items-center gap-2 py-1 group text-xs">
      <CircleDot className="h-3 w-3 text-blue-400 shrink-0" />
      <span className="flex-1 truncate">{zone.name || '—'}</span>
      <span className="text-muted-foreground font-mono text-[10px]">r={zone.radius}m</span>
      <Button variant="ghost" size="icon" className="h-4 w-4 opacity-0 group-hover:opacity-100 text-destructive" onClick={() => del.mutate()}><Trash2 className="h-2.5 w-2.5" /></Button>
    </div>
  )
}

function RoadRow({ road, mapId, onDeleted, t }: { road: RoadData; mapId: number; onDeleted: () => void; t: (k: string) => string }) {
  const api = useApi()
  const del = useMutation({ mutationFn: () => api.delete(`/maps/admin/maps/${mapId}/roads/${road.id}`), onSuccess: () => { onDeleted(); toast.success(t('mapAdmin.deleted')) }, onError: (e: Error) => toast.error(e.message) })
  return (
    <div className="flex items-center gap-2 py-1 group text-xs">
      <Route className="h-3 w-3 text-amber-400 shrink-0" />
      <span className="flex-1 truncate">{road.name || road.type}</span>
      <span className="text-muted-foreground font-mono text-[10px]">{Math.round(road.length)}m</span>
      <Button variant="ghost" size="icon" className="h-4 w-4 opacity-0 group-hover:opacity-100 text-destructive" onClick={() => del.mutate()}><Trash2 className="h-2.5 w-2.5" /></Button>
    </div>
  )
}

// ─── Inline Add Forms ──────────────────────────────────────────────────────────

function InlineAddLandmark({ mapId, t, onAdded }: { mapId: number; t: (k: string) => string; onAdded: () => void }) {
  const api = useApi()
  const [name, setName] = useState(''); const [x, setX] = useState(''); const [z, setZ] = useState('')
  const add = useMutation({
    mutationFn: () => api.post(`/maps/admin/maps/${mapId}/landmarks`, { name, type: 'poi', position_x: parseFloat(x), position_z: parseFloat(z) }),
    onSuccess: () => { onAdded(); setName(''); setX(''); setZ(''); toast.success(t('mapAdmin.added')) }, onError: (e: Error) => toast.error(e.message),
  })
  return (
    <div className="flex items-end gap-1 mt-2">
      <Input className="h-7 text-xs flex-1" placeholder={t('mapAdmin.landmarkName')} value={name} onChange={e => setName(e.target.value)} />
      <Input className="h-7 text-xs w-16" placeholder="X" type="number" value={x} onChange={e => setX(e.target.value)} />
      <Input className="h-7 text-xs w-16" placeholder="Z" type="number" value={z} onChange={e => setZ(e.target.value)} />
      <Button size="sm" className="h-7 px-2" onClick={() => add.mutate()} disabled={!name.trim() || !x || !z || add.isPending}><Plus className="h-3 w-3" /></Button>
    </div>
  )
}

function InlineAddZone({ mapId, t, onAdded }: { mapId: number; t: (k: string) => string; onAdded: () => void }) {
  const api = useApi()
  const [name, setName] = useState(''); const [cx, setCx] = useState(''); const [cz, setCz] = useState(''); const [radius, setRadius] = useState('100')
  const add = useMutation({
    mutationFn: () => api.post(`/maps/admin/maps/${mapId}/zones`, { name, type: 'area', center_x: parseFloat(cx), center_z: parseFloat(cz), radius: parseFloat(radius) }),
    onSuccess: () => { onAdded(); setName(''); setCx(''); setCz(''); setRadius('100'); toast.success(t('mapAdmin.added')) }, onError: (e: Error) => toast.error(e.message),
  })
  return (
    <div className="flex items-end gap-1 mt-2 flex-wrap">
      <Input className="h-7 text-xs flex-1 min-w-[80px]" placeholder={t('mapAdmin.zoneName')} value={name} onChange={e => setName(e.target.value)} />
      <Input className="h-7 text-xs w-14" placeholder="X" type="number" value={cx} onChange={e => setCx(e.target.value)} />
      <Input className="h-7 text-xs w-14" placeholder="Z" type="number" value={cz} onChange={e => setCz(e.target.value)} />
      <Input className="h-7 text-xs w-14" placeholder="R" type="number" value={radius} onChange={e => setRadius(e.target.value)} />
      <Button size="sm" className="h-7 px-2" onClick={() => add.mutate()} disabled={!name.trim() || !cx || !cz || add.isPending}><Plus className="h-3 w-3" /></Button>
    </div>
  )
}

function InlineAddRoad({ mapId, t, onAdded }: { mapId: number; t: (k: string) => string; onAdded: () => void }) {
  const api = useApi()
  const [sx, setSx] = useState(''); const [sz, setSz] = useState(''); const [ex, setEx] = useState(''); const [ez, setEz] = useState('')
  const add = useMutation({
    mutationFn: () => api.post(`/maps/admin/maps/${mapId}/roads`, { type: 'road', width: 6, points: [[parseFloat(sx), parseFloat(sz)], [parseFloat(ex), parseFloat(ez)]] }),
    onSuccess: () => { onAdded(); setSx(''); setSz(''); setEx(''); setEz(''); toast.success(t('mapAdmin.added')) }, onError: (e: Error) => toast.error(e.message),
  })
  return (
    <div className="flex items-end gap-1 mt-2 flex-wrap">
      <Input className="h-7 text-xs w-14" placeholder="SX" type="number" value={sx} onChange={e => setSx(e.target.value)} />
      <Input className="h-7 text-xs w-14" placeholder="SZ" type="number" value={sz} onChange={e => setSz(e.target.value)} />
      <span className="text-muted-foreground text-xs pb-1">&rarr;</span>
      <Input className="h-7 text-xs w-14" placeholder="EX" type="number" value={ex} onChange={e => setEx(e.target.value)} />
      <Input className="h-7 text-xs w-14" placeholder="EZ" type="number" value={ez} onChange={e => setEz(e.target.value)} />
      <Button size="sm" className="h-7 px-2" onClick={() => add.mutate()} disabled={!sx || !sz || !ex || !ez || add.isPending}><Plus className="h-3 w-3" /></Button>
    </div>
  )
}

// ─── Import Dialog ─────────────────────────────────────────────────────────────

const CHUNK_BATCH_SIZE = 20
const CHUNK_RETRY_LIMIT = 2

function ImportDialog({ t, onImported }: { t: (k: string) => string; onImported: () => void }) {
  const api = useApi()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const mainFileRef = useRef<HTMLInputElement>(null)
  const chunkFileRef = useRef<HTMLInputElement>(null)
  const scannerFileRef = useRef<HTMLInputElement>(null)
  const [importStep, setImportStep] = useState<1 | 2 | 3>(1)
  const [chunkUploadMapId, setChunkUploadMapId] = useState<number | null>(null)
  const [importProgress, setImportProgress] = useState('')
  const [chunkProgress, setChunkProgress] = useState<{
    totalFiles: number; totalBatches: number
    completedBatches: number; totalEntities: number; totalChunks: number
    failedBatchIdx: number | null; paused: boolean
  } | null>(null)
  const chunkAbortRef = useRef(false)
  const pendingFilesRef = useRef<File[]>([])

  const importMutation = useMutation({
    mutationFn: async (file: File) => { setImportProgress('Uploading mapdata.json...'); const fd = new FormData(); fd.append('file', file); return api.upload<Record<string, unknown>>('/maps/admin/maps/import', fd) },
    onSuccess: (data: Record<string, unknown>) => { queryClient.invalidateQueries({ queryKey: ['admin-maps'] }); setImportProgress(''); if (data?.id) { toast.success(t('mapAdmin.importSuccess')); setChunkUploadMapId(data.id as number); setImportStep(2) } else { toast.success(t('mapAdmin.importSuccess')); setOpen(false) } },
    onError: (err: Error) => { setImportProgress(''); toast.error(err.message) },
  })

  const uploadChunkBatches = useCallback(async (files: File[], startFromBatch = 0) => {
    if (!chunkUploadMapId) throw new Error('No map selected')
    const chunkFiles = files.filter(f => f.name.endsWith('.jsonl') || f.name.endsWith('.JSONL'))
    if (chunkFiles.length === 0) throw new Error('No .jsonl files found')

    pendingFilesRef.current = chunkFiles
    chunkAbortRef.current = false

    const batches: File[][] = []
    for (let i = 0; i < chunkFiles.length; i += CHUNK_BATCH_SIZE) {
      batches.push(chunkFiles.slice(i, i + CHUNK_BATCH_SIZE))
    }

    setChunkProgress({
      totalFiles: chunkFiles.length, totalBatches: batches.length,
      completedBatches: startFromBatch, totalEntities: 0, totalChunks: 0,
      failedBatchIdx: null, paused: false,
    })

    let accEntities = 0
    let accChunks = 0

    for (let bi = startFromBatch; bi < batches.length; bi++) {
      if (chunkAbortRef.current) {
        setChunkProgress(p => p ? { ...p, paused: true } : p)
        return
      }

      const batch = batches[bi]
      setImportProgress(`Uploading batch ${bi + 1}/${batches.length} (${batch.length} files)...`)

      let success = false
      for (let retry = 0; retry <= CHUNK_RETRY_LIMIT; retry++) {
        try {
          const fd = new FormData()
          for (const f of batch) fd.append('files', f)
          const res = await api.upload<{ chunks_imported?: number; entities_imported?: number }>(
            `/maps/admin/maps/${chunkUploadMapId}/import-chunks`, fd,
          )
          accChunks += res?.chunks_imported ?? 0
          accEntities += res?.entities_imported ?? 0
          success = true
          break
        } catch (err) {
          if (retry < CHUNK_RETRY_LIMIT) {
            setImportProgress(`Batch ${bi + 1} failed, retrying (${retry + 1}/${CHUNK_RETRY_LIMIT})...`)
            await new Promise(r => setTimeout(r, 1000))
          } else {
            setChunkProgress(p => p ? { ...p, failedBatchIdx: bi, paused: true, totalEntities: accEntities, totalChunks: accChunks } : p)
            setImportProgress(`Batch ${bi + 1} failed after ${CHUNK_RETRY_LIMIT} retries. Click Resume to continue.`)
            toast.error(`Batch ${bi + 1} failed: ${err instanceof Error ? err.message : 'Unknown error'}`)
            return
          }
        }
      }

      if (success) {
        setChunkProgress(p => p ? { ...p, completedBatches: bi + 1, totalEntities: accEntities, totalChunks: accChunks, failedBatchIdx: null } : p)
      }
    }

    setImportProgress('')
    setChunkProgress(null)
    queryClient.invalidateQueries({ queryKey: ['admin-maps'] })
    toast.success(`Imported ${accChunks} chunks, ${accEntities} entities`)
    setImportStep(3)
  }, [chunkUploadMapId, api, queryClient])

  const chunkImportMutation = useMutation({
    mutationFn: async (files: File[]) => uploadChunkBatches(files),
    onError: (err: Error) => { setImportProgress(''); toast.error(err.message) },
  })

  const handleResume = useCallback(() => {
    if (!chunkProgress || chunkProgress.failedBatchIdx == null) return
    const resumeFrom = chunkProgress.failedBatchIdx
    setChunkProgress(p => p ? { ...p, paused: false, failedBatchIdx: null } : p)
    uploadChunkBatches(pendingFilesRef.current, resumeFrom)
  }, [chunkProgress, uploadChunkBatches])

  const scannerMergeMutation = useMutation({
    mutationFn: async (file: File) => { setImportProgress('Uploading Scanner data for merge...'); const fd = new FormData(); fd.append('file', file); return api.upload<Record<string, unknown>>('/maps/admin/maps/import', fd) },
    onSuccess: (data: Record<string, unknown>) => { queryClient.invalidateQueries({ queryKey: ['admin-maps'] }); setImportProgress(''); if (data?.mode === 'merge') { toast.success(`Merged: ${data.landmarks_imported ?? 0} landmarks, ${data.roads_imported ?? 0} roads`) } else { toast.success(t('mapAdmin.importSuccess')) }; setOpen(false); setImportStep(1); setChunkUploadMapId(null); onImported() },
    onError: (err: Error) => { setImportProgress(''); toast.error(err.message) },
  })

  const chunkBusy = chunkImportMutation.isPending || (chunkProgress != null && !chunkProgress.paused)

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) { chunkAbortRef.current = true; setImportStep(1); setChunkUploadMapId(null); setChunkProgress(null); setImportProgress('') } }}>
      <DialogTrigger asChild><Button variant="ghost" size="icon" className="h-7 w-7" title={t('mapAdmin.importMap')}><Upload className="h-3.5 w-3.5" /></Button></DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>{t('mapAdmin.importMap')}</DialogTitle></DialogHeader>
        <div className="flex items-center gap-2 mb-2">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-1">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${importStep === s ? 'bg-primary text-primary-foreground' : importStep > s ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'}`}>
                {importStep > s ? '\u2713' : s}
              </div>
              <span className={`text-xs ${importStep === s ? 'font-medium' : 'text-muted-foreground'}`}>{s === 1 ? 'Exporter' : s === 2 ? 'Chunks' : 'Scanner'}</span>
              {s < 3 && <div className="w-6 h-px bg-border" />}
            </div>
          ))}
        </div>
        {importStep === 1 && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">Step 1: Select OA_MapExporter&apos;s mapdata.json.</p>
            <input ref={mainFileRef} type="file" accept=".json" className="hidden" onChange={(e) => { const file = e.target.files?.[0]; e.target.value = ''; if (file) importMutation.mutate(file) }} />
            <Button variant="outline" className="w-full h-20 border-dashed" onClick={() => mainFileRef.current?.click()} disabled={importMutation.isPending}>
              {importMutation.isPending ? <span className="text-sm">{importProgress || 'Importing...'}</span> : <div className="flex flex-col items-center gap-1"><FileJson className="h-5 w-5" /><span className="text-sm">Select Exporter mapdata.json</span></div>}
            </Button>
          </div>
        )}
        {importStep === 2 && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">Step 2: Import entity chunks (.jsonl). Files are uploaded in batches of {CHUNK_BATCH_SIZE}.</p>
            <input ref={chunkFileRef} type="file" accept=".jsonl" multiple className="hidden" onChange={(e) => { const selected = e.target.files; if (selected && selected.length > 0) { const fileArray = Array.from(selected); e.target.value = ''; chunkImportMutation.mutate(fileArray) } }} />
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => chunkFileRef.current?.click()} disabled={chunkBusy}><Upload className="h-4 w-4 mr-1" /> Select chunk files</Button>
              {chunkProgress?.paused && chunkProgress.failedBatchIdx != null && (
                <Button variant="default" onClick={handleResume}>Resume</Button>
              )}
              <Button variant="ghost" onClick={() => { chunkAbortRef.current = true; setImportStep(3) }} disabled={chunkBusy && !chunkProgress?.paused}>Skip</Button>
            </div>
            {chunkProgress && (
              <div className="space-y-2">
                <div className="w-full bg-muted rounded-full h-2.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${chunkProgress.failedBatchIdx != null ? 'bg-destructive' : 'bg-primary'}`}
                    style={{ width: `${Math.round((chunkProgress.completedBatches / chunkProgress.totalBatches) * 100)}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Batch {chunkProgress.completedBatches}/{chunkProgress.totalBatches} ({chunkProgress.totalFiles} files)</span>
                  <span>{chunkProgress.totalEntities.toLocaleString()} entities</span>
                </div>
              </div>
            )}
            {importProgress && <p className="text-sm text-primary animate-pulse">{importProgress}</p>}
          </div>
        )}
        {importStep === 3 && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">Step 3: Import OA_MapScanner data to merge.</p>
            <input ref={scannerFileRef} type="file" accept=".json" className="hidden" onChange={(e) => { const file = e.target.files?.[0]; e.target.value = ''; if (file) scannerMergeMutation.mutate(file) }} />
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1 h-16 border-dashed" onClick={() => scannerFileRef.current?.click()} disabled={scannerMergeMutation.isPending}>
                {scannerMergeMutation.isPending ? <span className="text-sm">{importProgress || 'Merging...'}</span> : <div className="flex flex-col items-center gap-1"><FileJson className="h-5 w-5" /><span className="text-sm">Select Scanner mapdata.json</span></div>}
              </Button>
              <Button variant="ghost" onClick={() => { setOpen(false); setImportStep(1); setChunkUploadMapId(null); onImported() }}>Done</Button>
            </div>
            {importProgress && <p className="text-sm text-primary animate-pulse">{importProgress}</p>}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

// ─── Create Map Dialog ─────────────────────────────────────────────────────────

function CreateMapDialog({ t, onCreated }: { t: (k: string) => string; onCreated: () => void }) {
  const api = useApi()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState(''); const [sizeX, setSizeX] = useState('10000'); const [sizeZ, setSizeZ] = useState('10000')
  const createMutation = useMutation({
    mutationFn: () => api.post('/maps/admin/maps/create', { name, size_x: parseFloat(sizeX), size_z: parseFloat(sizeZ) }),
    onSuccess: () => { onCreated(); setOpen(false); setName(''); setSizeX('10000'); setSizeZ('10000'); toast.success(t('mapAdmin.createSuccess')) },
    onError: (err: Error) => toast.error(err.message),
  })
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button variant="ghost" size="icon" className="h-7 w-7" title={t('mapAdmin.createMap')}><Plus className="h-3.5 w-3.5" /></Button></DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>{t('mapAdmin.createMap')}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2"><Label>{t('mapAdmin.mapName')}</Label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="My Map" /></div>
          <div className="space-y-2">
            <Label>{t('mapAdmin.mapSize')}</Label>
            <div className="grid grid-cols-2 gap-3">
              <div><Label className="text-xs text-muted-foreground">{t('mapAdmin.width')}</Label><Input type="number" min="100" value={sizeX} onChange={(e) => setSizeX(e.target.value)} /></div>
              <div><Label className="text-xs text-muted-foreground">{t('mapAdmin.height')}</Label><Input type="number" min="100" value={sizeZ} onChange={(e) => setSizeZ(e.target.value)} /></div>
            </div>
          </div>
          <Button className="w-full" onClick={() => createMutation.mutate()} disabled={!name.trim() || createMutation.isPending}>{t('mapAdmin.createMap')}</Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ─── Admin Right Panel ─────────────────────────────────────────────────────────

function AdminPanel({
  maps, selectedMap, onSelectMap, selectedMapData, t, locale,
}: {
  maps: GameMap[]; selectedMap: number | null; onSelectMap: (id: number | null) => void; selectedMapData: GameMap | undefined
  t: (k: string, params?: Record<string, string | number>) => string; locale: string
}) {
  const api = useApi()
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [sourceFilter, setSourceFilter] = useState<string>('all')
  const [showAddLandmark, setShowAddLandmark] = useState(false)
  const [showAddZone, setShowAddZone] = useState(false)
  const [showAddRoad, setShowAddRoad] = useState(false)
  const [hexProviderId, setHexProviderId] = useState<string>('')
  const [hexModelName, setHexModelName] = useState<string>('')
  const [hexBatchSize, setHexBatchSize] = useState<string>('20')
  const [batchTestResult, setBatchTestResult] = useState<{ success: boolean; msg: string } | null>(null)
  const [batchTesting, setBatchTesting] = useState(false)

  const { data: llmProviders } = useQuery({ queryKey: ['llm-providers'], queryFn: () => api.get<{ items: { id: number; name: string; provider_type: string; models: { name: string }[] | null }[] }>('/llm-providers') })
  const hexSelectedProvider = llmProviders?.items?.find((p) => String(p.id) === hexProviderId)

  const filteredMaps = useMemo(() => {
    let result = maps
    if (sourceFilter !== 'all') result = result.filter(m => m.source === sourceFilter)
    if (searchTerm.trim()) { const q = searchTerm.toLowerCase(); result = result.filter(m => m.name.toLowerCase().includes(q)) }
    return result
  }, [maps, sourceFilter, searchTerm])

  const mapId = selectedMap
  const mapData = selectedMapData

  const { data: layers } = useQuery({ queryKey: ['map-layers', mapId], queryFn: () => api.get<MapLayer[]>(`/maps/admin/maps/${mapId}/layers`), enabled: !!mapId })
  const { data: landmarks } = useQuery({ queryKey: ['map-landmarks-admin', mapId], queryFn: () => api.get<LandmarkData[]>(`/maps/admin/maps/${mapId}/landmarks?limit=2000`), enabled: !!mapId })
  const { data: zones } = useQuery({ queryKey: ['map-zones-admin', mapId], queryFn: () => api.get<ZoneData[]>(`/maps/admin/maps/${mapId}/zones`), enabled: !!mapId })
  const { data: roads } = useQuery({ queryKey: ['map-roads-admin', mapId], queryFn: () => api.get<RoadData[]>(`/maps/admin/maps/${mapId}/roads`), enabled: !!mapId })
  const { data: tileInfo } = useQuery({ queryKey: ['tile-info', mapId], queryFn: () => api.get<{ has_satellite_tiles: boolean; tile_min_zoom: number; tile_max_zoom: number; available_zooms: number[]; overview_grid_size: number; tile_url_template: string; tile_dir_exists: boolean; tile_dir_path: string; has_military_tiles?: boolean; military_zooms?: number[]; military_grid_size?: number; military_url_template?: string; analysis_tiles?: Record<string, { ready: boolean; zooms: number[]; url_template: string }> }>(`/maps/admin/maps/${mapId}/tiles/info`), enabled: !!mapId })

  const publishMutation = useMutation({ mutationFn: (id: number) => api.put(`/maps/admin/maps/${id}`, { status: 'published' }), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-maps'] }); toast.success(t('mapAdmin.published')) } })
  const deleteMutation = useMutation({ mutationFn: (id: number) => api.delete(`/maps/admin/maps/${id}`), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-maps'] }); onSelectMap(null); toast.success(t('common.deleted')) } })
  const toggleSatelliteMutation = useMutation({ mutationFn: (enabled: boolean) => api.put(`/maps/admin/maps/${mapId}`, { has_satellite_tiles: enabled }), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-maps'] }); queryClient.invalidateQueries({ queryKey: ['tile-info', mapId] }); toast.success(t('common.saved')) }, onError: (err: Error) => toast.error(err.message) })
  const createTileDirMutation = useMutation({ mutationFn: () => api.post<{ tile_dir_path: string }>(`/maps/admin/maps/${mapId}/tiles/create-dir`, {}), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['tile-info', mapId] }); toast.success(t('mapAdmin.tileDirCreated')) }, onError: (err: Error) => toast.error(err.message) })
  const hexGenMutation = useMutation({ mutationFn: () => { const params = new URLSearchParams(); if (hexProviderId) params.set('provider_id', hexProviderId); if (hexModelName) params.set('model_name', hexModelName); const bs = parseInt(hexBatchSize, 10); if (bs > 0) params.set('batch_size', String(bs)); const qs = params.toString(); return api.post(`/maps/admin/maps/${mapId}/generate-hex-cells${qs ? `?${qs}` : ''}`) }, onSuccess: () => { startBgPoll(); toast.success(t('mapAdmin.hexCellsStarted') || 'Hex cell generation started') }, onError: (err: Error) => toast.error(err.message) })
  const testBatchSize = useCallback(async () => {
    if (!hexProviderId || !hexModelName) { toast.error('Select provider and model first'); return }
    setBatchTesting(true); setBatchTestResult(null)
    try {
      const bs = parseInt(hexBatchSize, 10) || 20
      const params = new URLSearchParams({ provider_id: hexProviderId, model_name: hexModelName, batch_size: String(bs) })
      const res = await api.post<{ success: boolean; batch_size: number; embeddings_returned?: number; dimensions?: number; elapsed_seconds?: number; error?: string }>(`/maps/admin/test-embedding-batch?${params}`)
      if (res.success) {
        setBatchTestResult({ success: true, msg: `batch_size=${bs} OK (${res.dimensions}d, ${res.elapsed_seconds}s)` })
      } else {
        setBatchTestResult({ success: false, msg: `batch_size=${bs} failed: ${res.error?.slice(0, 100)}` })
      }
    } catch (err) { setBatchTestResult({ success: false, msg: err instanceof Error ? err.message : 'Test failed' }) }
    finally { setBatchTesting(false) }
  }, [hexProviderId, hexModelName, hexBatchSize, api])
  const [bgGenerating, setBgGenerating] = useState(false)
  const bgTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const startBgPoll = useCallback(() => {
    setBgGenerating(true)
    if (bgTimerRef.current) clearTimeout(bgTimerRef.current)
    bgTimerRef.current = setTimeout(() => setBgGenerating(false), 30_000)
  }, [])
  const militaryGenMutation = useMutation({ mutationFn: () => api.post(`/maps/admin/maps/${mapId}/generate-military-tiles`), onSuccess: () => { startBgPoll(); toast.success(t('mapAdmin.militaryTilesStarted') || 'Military tile generation started') }, onError: (err: Error) => toast.error(err.message) })

  const [generatingLayers, setGeneratingLayers] = useState<Set<string>>(new Set())
  const generateAnalysisTiles = useCallback(async (layer: string) => {
    setGeneratingLayers(prev => new Set(prev).add(layer))
    try {
      await api.post(`/maps/admin/maps/${mapId}/generate-analysis-tiles/${layer}`)
      startBgPoll()
      toast.success(t('mapAdmin.analysisTilesStarted', { layer }) || `${layer} tile generation started`)
    } catch (err: any) {
      toast.error(err?.message || 'Failed')
    } finally {
      setGeneratingLayers(prev => { const next = new Set(prev); next.delete(layer); return next })
    }
  }, [api, mapId, startBgPoll, t])
  const generateAllAnalysisTiles = useCallback(async () => {
    const allLayers = ['vegetation', 'builtup', 'slope', 'hillshade', 'contours', 'water', 'trafficability', 'cover', 'mcoo']
    for (const layer of allLayers) {
      await generateAnalysisTiles(layer)
    }
  }, [generateAnalysisTiles])

  type TileProgress = Record<string, { done: number; total: number; status: string; layer: string }>
  const [tileGenProgress, setTileGenProgress] = useState<TileProgress>({})
  const anyGenerating = militaryGenMutation.isPending || generatingLayers.size > 0 || hexGenMutation.isPending
  const hasActiveProgress = Object.keys(tileGenProgress).length > 0
  const shouldPoll = anyGenerating || hasActiveProgress || bgGenerating
  useEffect(() => {
    if (!mapId) return
    let cancelled = false
    let prevHadProgress = hasActiveProgress
    const poll = async () => {
      try {
        const data = await api.get<TileProgress>(`/maps/admin/maps/${mapId}/tile-gen-progress`)
        if (!cancelled) {
          setTileGenProgress(data || {})
          const nowHas = Object.keys(data || {}).length > 0
          if (nowHas) {
            setBgGenerating(true)
            if (bgTimerRef.current) clearTimeout(bgTimerRef.current)
            bgTimerRef.current = setTimeout(() => setBgGenerating(false), 30_000)
          }
          if (prevHadProgress && !nowHas) {
            setBgGenerating(false)
            queryClient.invalidateQueries({ queryKey: ['tile-info', mapId] })
          }
          prevHadProgress = nowHas
        }
      } catch { /* ignore */ }
    }
    poll()
    if (!shouldPoll) return
    const id = setInterval(poll, 2000)
    return () => { cancelled = true; clearInterval(id) }
  }, [mapId, shouldPoll, hasActiveProgress, api, queryClient])

  const sortedLayers = [...(layers || [])].sort((a, b) => b.z_index - a.z_index)
  const swapLayerOrder = useMutation({ mutationFn: async ({ aId, aZ, bId, bZ }: { aId: number; aZ: number; bId: number; bZ: number }) => { await Promise.all([api.put(`/maps/admin/maps/${mapId}/layers/${aId}`, { z_index: bZ }), api.put(`/maps/admin/maps/${mapId}/layers/${bId}`, { z_index: aZ })]) }, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['map-layers', mapId] }), onError: (err: Error) => toast.error(err.message) })
  function moveLayer(idx: number, dir: -1 | 1) { const target = idx + dir; if (target < 0 || target >= sortedLayers.length) return; const a = sortedLayers[idx], b = sortedLayers[target]; swapLayerOrder.mutate({ aId: a.id, aZ: a.z_index, bId: b.id, bZ: b.z_index }) }

  function invalidateLayers() { queryClient.invalidateQueries({ queryKey: ['map-layers', mapId] }) }
  function invalidateLandmarks() { queryClient.invalidateQueries({ queryKey: ['map-landmarks-admin', mapId] }); queryClient.invalidateQueries({ queryKey: ['map-landmarks', mapId] }) }
  function invalidateZones() { queryClient.invalidateQueries({ queryKey: ['map-zones-admin', mapId] }); queryClient.invalidateQueries({ queryKey: ['map-zones', mapId] }) }
  function invalidateRoads() { queryClient.invalidateQueries({ queryKey: ['map-roads-admin', mapId] }); queryClient.invalidateQueries({ queryKey: ['map-roads', mapId] }) }
  function invalidateMaps() { queryClient.invalidateQueries({ queryKey: ['admin-maps'] }) }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 pt-3 pb-2 shrink-0">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold">{t('mapAdmin.title')}</h2>
          <div className="flex items-center gap-0.5">
            <ImportDialog t={t} onImported={invalidateMaps} />
            <CreateMapDialog t={t} onCreated={invalidateMaps} />
          </div>
        </div>
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
          <Input className="h-7 text-xs pl-7" placeholder="Search maps..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
        </div>
        <div className="flex gap-1 mt-2">
          {(['all', 'workbench', 'scanner', 'manual'] as const).map(f => (
            <button key={f} onClick={() => setSourceFilter(f)} className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${sourceFilter === f ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:text-foreground'}`}>
              {f === 'all' ? t('common.all') : f === 'manual' ? t('mapAdmin.sourceManual') : f === 'workbench' ? 'WB' : t('mapAdmin.sourceScanner')}
            </button>
          ))}
        </div>
      </div>
      <Separator />
      <ScrollArea className="flex-1 min-h-0">
        <div className="px-2 py-1 space-y-0.5">
          {filteredMaps.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Globe className="h-8 w-8 text-muted-foreground/40 mb-2" />
              <p className="text-xs text-muted-foreground">{t('mapAdmin.emptyTitle')}</p>
            </div>
          ) : filteredMaps.map(m => (
            <button key={m.id} onClick={() => onSelectMap(selectedMap === m.id ? null : m.id)}
              className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors group ${selectedMap === m.id ? 'bg-primary/10 border border-primary/30' : 'hover:bg-muted/60 border border-transparent'}`}>
              <div className="flex items-center justify-between gap-2">
                <span className={`text-sm font-medium truncate ${selectedMap === m.id ? 'text-primary' : ''}`}>{m.name}</span>
                <Badge variant={m.status === 'published' ? 'default' : 'secondary'} className="text-[10px] h-4 px-1">{m.status === 'published' ? 'P' : 'D'}</Badge>
              </div>
              <p className="text-[11px] text-muted-foreground mt-0.5">{m.size_x}m × {m.size_z}m{m.source && ` · ${m.source === 'scanner' ? t('mapAdmin.sourceScanner') : m.source === 'workbench' ? 'WB' : t('mapAdmin.sourceManual')}`}</p>
            </button>
          ))}
        </div>
      </ScrollArea>

      {mapId && mapData && (
        <>
          <Separator />
          <div className="shrink-0 px-3 py-2 bg-muted/30">
            <div className="flex items-center justify-between">
              <div className="min-w-0"><p className="text-sm font-semibold truncate">{mapData.name}</p><p className="text-[10px] text-muted-foreground">{mapData.size_x}m × {mapData.size_z}m</p></div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild><Button variant="ghost" size="icon" className="h-7 w-7"><MoreHorizontal className="h-3.5 w-3.5" /></Button></DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-40">
                  {mapData.status === 'draft' && <DropdownMenuItem onClick={() => publishMutation.mutate(mapId)}>{t('mapAdmin.publish')}</DropdownMenuItem>}
                  <DropdownMenuSeparator />
                  <AlertDialog>
                    <AlertDialogTrigger asChild><DropdownMenuItem className="text-destructive focus:text-destructive" onSelect={e => e.preventDefault()}><Trash2 className="h-3.5 w-3.5 mr-2" />{t('common.delete')}</DropdownMenuItem></AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader><AlertDialogTitle>{t('common.confirmDelete')}</AlertDialogTitle><AlertDialogDescription>{t('mapAdmin.confirmDeleteMap')}</AlertDialogDescription></AlertDialogHeader>
                      <AlertDialogFooter><AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel><AlertDialogAction onClick={() => deleteMutation.mutate(mapId)}>{t('common.delete')}</AlertDialogAction></AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
          <Separator />
          <ScrollArea className="flex-1 min-h-0">
            <div className="py-1">
              {/* Generation */}
              <PanelSection title={t('mapAdmin.militaryMap')} icon={<MapIcon className="h-3.5 w-3.5" />} defaultOpen>
                <div className="space-y-2">
                  <p className="text-[10px] text-muted-foreground">{t('mapAdmin.militaryMapHint')}</p>
                  {tileInfo?.has_military_tiles && !tileGenProgress.military && <Badge variant="outline" className="text-[10px] bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800">{t('mapAdmin.militaryTilesReady')}</Badge>}
                  <Button size="sm" variant={tileInfo?.has_military_tiles ? 'outline' : 'default'} className="w-full h-7 text-xs" onClick={() => militaryGenMutation.mutate()} disabled={militaryGenMutation.isPending}>
                    <MapIcon className="h-3 w-3 mr-1" />{militaryGenMutation.isPending ? t('mapAdmin.generatingMilitaryTiles') : tileInfo?.has_military_tiles ? t('mapAdmin.regenerateMilitaryTiles') : t('mapAdmin.generateMilitaryTiles')}
                  </Button>
                  {tileGenProgress.military && (
                    <TileProgressBar label="Military" done={tileGenProgress.military.done} total={tileGenProgress.military.total} />
                  )}
                </div>
              </PanelSection>

              {/* Analysis Tiles */}
              <PanelSection title={t('mapAdmin.analysisTiles')} icon={<Layers className="h-3.5 w-3.5" />}>
                <div className="space-y-1.5">
                  <p className="text-[10px] text-muted-foreground">{t('mapAdmin.analysisTilesHint')}</p>
                  {(['vegetation', 'builtup', 'slope', 'hillshade', 'contours', 'water', 'trafficability', 'cover', 'mcoo'] as const).map(layer => {
                    const ready = !!tileInfo?.analysis_tiles?.[layer === 'contours' ? 'contour' : layer]?.ready
                    const generating = generatingLayers.has(layer)
                    const prog = tileGenProgress[layer]
                    return (
                      <div key={layer} className="space-y-0.5">
                        <div className="flex items-center justify-between gap-1">
                          <div className="flex items-center gap-1 min-w-0">
                            {ready && !prog && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />}
                            {!ready && !prog && <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30 shrink-0" />}
                            {prog && <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse shrink-0" />}
                            <span className="text-[10px] truncate">{t(`thematic.${layer}`)}</span>
                          </div>
                          <Button size="sm" variant={ready ? 'outline' : 'default'} className="h-5 text-[9px] px-1.5 shrink-0" onClick={() => generateAnalysisTiles(layer)} disabled={generating}>
                            {generating ? '...' : ready ? t('mapAdmin.regenerate') : t('mapAdmin.generate')}
                          </Button>
                        </div>
                        {prog && <TileProgressBar label={layer} done={prog.done} total={prog.total} compact />}
                      </div>
                    )
                  })}
                  <Button size="sm" variant="outline" className="w-full h-7 text-xs mt-2" onClick={generateAllAnalysisTiles} disabled={generatingLayers.size > 0}>
                    <Layers className="h-3 w-3 mr-1" />{generatingLayers.size > 0 ? t('mapAdmin.generatingAnalysisTiles') : t('mapAdmin.generateAllAnalysisTiles')}
                  </Button>
                </div>
              </PanelSection>

              {/* Terrain Tiles */}
              <PanelSection title={t('mapAdmin.terrainTiles')} icon={<Landmark className="h-3.5 w-3.5" />}>
                <div className="space-y-1.5">
                  <p className="text-[10px] text-muted-foreground">{t('mapAdmin.terrainTilesHint')}</p>
                  {(['vegetation_real', 'buildings_real', 'roads', 'features'] as const).map(layer => {
                    const ready = !!tileInfo?.analysis_tiles?.[layer]?.ready
                    const generating = generatingLayers.has(layer)
                    const prog = tileGenProgress[layer]
                    return (
                      <div key={layer} className="space-y-0.5">
                        <div className="flex items-center justify-between gap-1">
                          <div className="flex items-center gap-1 min-w-0">
                            {ready && !prog && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />}
                            {!ready && !prog && <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30 shrink-0" />}
                            {prog && <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse shrink-0" />}
                            <span className="text-[10px] truncate">{t(`thematic.${layer}`)}</span>
                          </div>
                          <Button size="sm" variant={ready ? 'outline' : 'default'} className="h-5 text-[9px] px-1.5 shrink-0" onClick={() => generateAnalysisTiles(layer)} disabled={generating}>
                            {generating ? '...' : ready ? t('mapAdmin.regenerate') : t('mapAdmin.generate')}
                          </Button>
                        </div>
                        {prog && <TileProgressBar label={layer} done={prog.done} total={prog.total} compact />}
                      </div>
                    )
                  })}
                </div>
              </PanelSection>

              {/* Satellite Settings */}
              <PanelSection title={t('mapAdmin.satellite')} icon={<Satellite className="h-3.5 w-3.5" />} defaultOpen={mapData.has_satellite_tiles}>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs">{t('mapAdmin.satelliteToggle')}</span>
                    <Button variant={mapData.has_satellite_tiles ? 'default' : 'outline'} size="sm" className="h-6 text-[10px] px-2" onClick={() => toggleSatelliteMutation.mutate(!mapData.has_satellite_tiles)} disabled={toggleSatelliteMutation.isPending}>
                      {mapData.has_satellite_tiles ? t('mapAdmin.satelliteEnabled') : t('mapAdmin.satelliteDisabled')}
                    </Button>
                  </div>
                  {tileInfo && !tileInfo.tile_dir_exists && <Button size="sm" variant="outline" className="w-full h-7 text-xs" onClick={() => createTileDirMutation.mutate()} disabled={createTileDirMutation.isPending}><FolderPlus className="h-3 w-3 mr-1" />{t('mapAdmin.createTileDir')}</Button>}
                  {tileInfo?.tile_dir_exists && <Badge variant="outline" className="text-[10px] bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800">{t('mapAdmin.tileDirReady')}</Badge>}
                  {tileInfo?.tile_dir_path && <code className="block text-[10px] bg-muted p-1.5 rounded font-mono break-all">{tileInfo.tile_dir_path}</code>}
                </div>
              </PanelSection>

              {/* Landmarks */}
              <PanelSection title={t('mapAdmin.landmarks')} icon={<MapPin className="h-3.5 w-3.5" />} count={landmarks?.length ?? 0}>
                <div className="space-y-0">{(landmarks || []).slice(0, 50).map(lm => <LandmarkRow key={lm.id} lm={lm} mapId={mapId} onDeleted={invalidateLandmarks} t={t} locale={locale} />)}{(landmarks?.length ?? 0) > 50 && <p className="text-[10px] text-muted-foreground text-center py-1">+{(landmarks?.length ?? 0) - 50} more</p>}</div>
                {showAddLandmark ? <InlineAddLandmark mapId={mapId} t={t} onAdded={invalidateLandmarks} /> : <Button variant="ghost" size="sm" className="w-full h-6 text-[10px] mt-1" onClick={() => setShowAddLandmark(true)}><Plus className="h-3 w-3 mr-1" />{t('mapAdmin.addLandmark')}</Button>}
              </PanelSection>

              {/* Zones */}
              <PanelSection title={t('mapAdmin.zones')} icon={<CircleDot className="h-3.5 w-3.5" />} count={zones?.length ?? 0}>
                <div className="space-y-0">{(zones || []).map(z => <ZoneRow key={z.id} zone={z} mapId={mapId} onDeleted={invalidateZones} t={t} />)}</div>
                {showAddZone ? <InlineAddZone mapId={mapId} t={t} onAdded={invalidateZones} /> : <Button variant="ghost" size="sm" className="w-full h-6 text-[10px] mt-1" onClick={() => setShowAddZone(true)}><Plus className="h-3 w-3 mr-1" />{t('mapAdmin.addZone')}</Button>}
              </PanelSection>

              {/* Roads */}
              <PanelSection title={t('mapAdmin.roads')} icon={<Route className="h-3.5 w-3.5" />} count={roads?.length ?? 0}>
                <div className="space-y-0">{(roads || []).map(r => <RoadRow key={r.id} road={r} mapId={mapId} onDeleted={invalidateRoads} t={t} />)}</div>
                {showAddRoad ? <InlineAddRoad mapId={mapId} t={t} onAdded={invalidateRoads} /> : <Button variant="ghost" size="sm" className="w-full h-6 text-[10px] mt-1" onClick={() => setShowAddRoad(true)}><Plus className="h-3 w-3 mr-1" />{t('mapAdmin.addRoad')}</Button>}
              </PanelSection>

              {/* Layers */}
              <PanelSection title={t('mapAdmin.layers')} icon={<Layers className="h-3.5 w-3.5" />} count={layers?.length ?? 0}>
                <div className="space-y-0.5">{sortedLayers.map((layer, idx) => <LayerRow key={layer.id} layer={layer} mapId={mapId} t={t} isFirst={idx === 0} isLast={idx === sortedLayers.length - 1} onMoveUp={() => moveLayer(idx, -1)} onMoveDown={() => moveLayer(idx, 1)} />)}</div>
              </PanelSection>

              {/* Terrain Intelligence */}
              <PanelSection title={t('mapAdmin.terrainIntel')} icon={<Hexagon className="h-3.5 w-3.5" />}>
                <p className="text-[10px] text-muted-foreground mb-2">{t('mapAdmin.hexCellsHint')}</p>
                <div className="space-y-2 mb-2">
                  <div className="space-y-1">
                    <Label className="text-[10px]">{t('mapAdmin.embeddingProvider')}</Label>
                    <Select value={hexProviderId} onValueChange={(v) => { setHexProviderId(v); setHexModelName('') }}>
                      <SelectTrigger className="h-7 text-xs"><SelectValue placeholder={t('mapAdmin.selectProvider')} /></SelectTrigger>
                      <SelectContent>{llmProviders?.items?.map((p) => <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  {hexProviderId && hexSelectedProvider?.models?.length ? (
                    <div className="space-y-1">
                      <Label className="text-[10px]">{t('mapAdmin.embeddingModel')}</Label>
                      <Select value={hexModelName} onValueChange={setHexModelName}>
                        <SelectTrigger className="h-7 text-xs"><SelectValue placeholder={t('mapAdmin.selectModel')} /></SelectTrigger>
                        <SelectContent>{hexSelectedProvider.models.map((m) => <SelectItem key={m.name} value={m.name}>{m.name}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                  ) : null}
                  {hexProviderId && hexModelName && (
                    <div className="space-y-1">
                      <Label className="text-[10px]">Batch Size</Label>
                      <div className="flex gap-1.5">
                        <Input type="number" min={1} max={100} className="h-7 text-xs flex-1" value={hexBatchSize} onChange={(e) => { setHexBatchSize(e.target.value); setBatchTestResult(null) }} />
                        <Button size="sm" variant="ghost" className="h-7 text-xs px-2 shrink-0" onClick={testBatchSize} disabled={batchTesting}>
                          {batchTesting ? '...' : t('mapAdmin.testBatch')}
                        </Button>
                      </div>
                      {batchTestResult && (
                        <p className={`text-[9px] ${batchTestResult.success ? 'text-emerald-600 dark:text-emerald-400' : 'text-destructive'}`}>
                          {batchTestResult.msg}
                        </p>
                      )}
                    </div>
                  )}
                </div>
                <Button size="sm" variant="outline" className="w-full h-7 text-xs" onClick={() => hexGenMutation.mutate()} disabled={hexGenMutation.isPending}>
                  <Hexagon className="h-3 w-3 mr-1" />{hexGenMutation.isPending ? t('mapAdmin.generatingHexCells') : t('mapAdmin.generateHexCells')}
                </Button>
                {tileGenProgress.hex_cells && (
                  <TileProgressBar label={`Hex Cells (${tileGenProgress.hex_cells.status})`} done={tileGenProgress.hex_cells.done} total={tileGenProgress.hex_cells.total} />
                )}
              </PanelSection>
            </div>
          </ScrollArea>
        </>
      )}
    </div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

export default function MapsPage() {
  const api = useApi()
  const queryClient = useQueryClient()
  const { t, locale } = useI18n()
  const user = useAuthStore(s => s.user)
  const isAdmin = user?.is_superuser || user?.is_staff || false

  const [selectedMap, setSelectedMap] = useState<number | null>(null)
  const [panelOpen, setPanelOpen] = useState(true)
  const [baseMapMode, setBaseMapMode] = useState<BaseMapMode>('military')

  const [dataLayerVisibility, setDataLayerVisibility] = useState({
    landmarks: false, roads: false, zones: false, grid: true,
  })
  const [hiddenLandmarkTypes, setHiddenLandmarkTypes] = useState<Set<string>>(new Set())
  const [hiddenZoneTypes, setHiddenZoneTypes] = useState<Set<string>>(new Set())
  const [hiddenRoadTypes, setHiddenRoadTypes] = useState<Set<string>>(new Set())

  const { data: maps, isLoading } = useQuery({
    queryKey: ['admin-maps'],
    queryFn: () => api.get<GameMap[]>('/maps/admin/maps'),
  })

  const selectedMapData = (maps || []).find(m => m.id === selectedMap)

  // Auto-select first published map for non-admin users
  const effectiveSelectedMap = useMemo(() => {
    if (selectedMap) return selectedMap
    const published = (maps || []).filter(m => m.status === 'published')
    return published.length > 0 ? published[0].id : null
  }, [selectedMap, maps])

  const effectiveMapData = (maps || []).find(m => m.id === effectiveSelectedMap)

  const { data: landmarks } = useQuery({
    queryKey: ['map-landmarks', effectiveSelectedMap],
    queryFn: () => api.get<LandmarkData[]>(`/maps/admin/maps/${effectiveSelectedMap}/landmarks?limit=2000`),
    enabled: !!effectiveSelectedMap,
  })
  const { data: zones } = useQuery({
    queryKey: ['map-zones', effectiveSelectedMap],
    queryFn: () => api.get<ZoneData[]>(`/maps/admin/maps/${effectiveSelectedMap}/zones`),
    enabled: !!effectiveSelectedMap,
  })
  const { data: roads } = useQuery({
    queryKey: ['map-roads', effectiveSelectedMap],
    queryFn: () => api.get<RoadData[]>(`/maps/admin/maps/${effectiveSelectedMap}/roads`),
    enabled: !!effectiveSelectedMap,
  })
  const { data: tileInfo } = useQuery({
    queryKey: ['tile-info', effectiveSelectedMap],
    queryFn: () => api.get<{ tile_url_template: string; overview_grid_size: number; has_military_tiles?: boolean; military_url_template?: string; military_grid_size?: number; has_satellite_tiles?: boolean; analysis_tiles?: Record<string, { ready: boolean; zooms: number[]; url_template: string }> }>(`/maps/admin/maps/${effectiveSelectedMap}/tiles/info`),
    enabled: !!effectiveSelectedMap,
  })

  const filteredLandmarks = useMemo(() => {
    if (!dataLayerVisibility.landmarks) return []
    return (landmarks || []).filter(lm => !hiddenLandmarkTypes.has(lm.type))
  }, [landmarks, hiddenLandmarkTypes, dataLayerVisibility.landmarks])

  const filteredZones = useMemo(() => {
    if (!dataLayerVisibility.zones) return []
    return (zones || []).filter(z => !hiddenZoneTypes.has(z.type))
  }, [zones, hiddenZoneTypes, dataLayerVisibility.zones])

  const filteredRoads = useMemo(() => {
    if (!dataLayerVisibility.roads) return []
    return (roads || []).filter(r => !hiddenRoadTypes.has(r.type))
  }, [roads, hiddenRoadTypes, dataLayerVisibility.roads])

  const landmarkTypes = useMemo(() => {
    const counts = new Map<string, number>()
    ;(landmarks || []).forEach(lm => counts.set(lm.type, (counts.get(lm.type) || 0) + 1))
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]) as [string, number][]
  }, [landmarks])

  const roadTypes = useMemo(() => {
    const counts = new Map<string, number>()
    ;(roads || []).forEach(r => counts.set(r.type, (counts.get(r.type) || 0) + 1))
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]) as [string, number][]
  }, [roads])

  const zoneTypes = useMemo(() => {
    const counts = new Map<string, number>()
    ;(zones || []).forEach(z => counts.set(z.type, (counts.get(z.type) || 0) + 1))
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]) as [string, number][]
  }, [zones])

  const toggleType = useCallback((setter: React.Dispatch<React.SetStateAction<Set<string>>>) => (type: string) => {
    setter(prev => { const next = new Set(prev); next.has(type) ? next.delete(type) : next.add(type); return next })
  }, [])

  const handleDataLayerChange = useCallback((layer: keyof typeof dataLayerVisibility, visible: boolean) => {
    setDataLayerVisibility(prev => ({ ...prev, [layer]: visible }))
  }, [])

  if (isLoading) return <CardLoadingState />

  const hasMilitary = !!tileInfo?.has_military_tiles && !!tileInfo?.military_url_template
  const hasSatellite = !!effectiveMapData?.has_satellite_tiles && !!tileInfo?.tile_url_template

  const effectiveBase = baseMapMode === 'satellite' && hasSatellite ? 'satellite' : hasMilitary ? 'military' : 'satellite'
  const tileUrl = effectiveBase === 'military' && tileInfo?.military_url_template
    ? `${getBackendOrigin()}${tileInfo.military_url_template}`
    : tileInfo?.tile_url_template
      ? `${getBackendOrigin()}${tileInfo.tile_url_template}`
      : undefined

  const satelliteOverlayUrl = effectiveBase === 'military' && hasSatellite
    ? `${getBackendOrigin()}${tileInfo!.tile_url_template}`
    : undefined

  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex-1 relative min-w-0">
        {effectiveMapData && tileUrl ? (
          <ReforgerMapViewer
            mapId={effectiveMapData.id}
            mapName={effectiveMapData.name}
            canvasWidth={effectiveMapData.size_x}
            canvasHeight={effectiveMapData.size_z}
            tileUrlTemplate={tileUrl}
            tileMinZoom={effectiveMapData.tile_min_zoom}
            tileMaxZoom={effectiveMapData.tile_max_zoom}
            overviewGridSize={effectiveBase === 'military' ? (tileInfo?.military_grid_size || tileInfo?.overview_grid_size || 1) : (tileInfo?.overview_grid_size || 1)}
            satelliteTileUrl={satelliteOverlayUrl}
            landmarks={filteredLandmarks}
            zones={filteredZones}
            roads={filteredRoads}
            showLandmarks={dataLayerVisibility.landmarks}
            showZones={dataLayerVisibility.zones}
            showRoads={dataLayerVisibility.roads}
            showGrid={dataLayerVisibility.grid}
            locale={locale}
            mapId_forLayers={effectiveMapData.id}
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
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-muted/20">
            <div className="text-center space-y-3">
              <Globe className="h-16 w-16 text-muted-foreground/30 mx-auto" />
              <div>
                <p className="text-lg font-medium text-muted-foreground">{effectiveMapData ? effectiveMapData.name : t('mapAdmin.emptyTitle')}</p>
                <p className="text-sm text-muted-foreground/60 mt-1">{effectiveMapData ? `${effectiveMapData.size_x}m × ${effectiveMapData.size_z}m — ${t('mapAdmin.noTilesHint')}` : t('mapAdmin.emptyDesc')}</p>
              </div>
            </div>
          </div>
        )}

        {/* Top-right controls */}
        <div className="absolute top-3 right-3 z-[1000] flex items-center gap-2">
          <MapSelector
            maps={maps || []}
            selectedMapId={effectiveSelectedMap}
            onSelect={setSelectedMap}
            isAdmin={isAdmin}
          />
          {isAdmin && (
            <Button variant="secondary" size="icon" className="h-8 w-8 shadow-md" onClick={() => setPanelOpen(!panelOpen)}>
              {panelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
            </Button>
          )}
        </div>
      </div>

      {/* Admin Panel — only visible to admin users */}
      {isAdmin && panelOpen && (
        <aside className="w-80 border-l bg-background flex flex-col shrink-0 overflow-hidden">
          <AdminPanel
            maps={maps || []}
            selectedMap={selectedMap}
            onSelectMap={setSelectedMap}
            selectedMapData={selectedMapData}
            t={t}
            locale={locale}
          />
        </aside>
      )}
    </div>
  )
}
