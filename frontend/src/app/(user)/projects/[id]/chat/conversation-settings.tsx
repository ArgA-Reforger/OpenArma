'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import {
  Bot, Workflow, BookOpen, Plug, X, Plus, Settings, Map,
  Swords, Copy, RefreshCw, ExternalLink, Save, Play, Square,
  Users, Clock, Crosshair, Activity, Trash2,
  ChevronDown, ChevronUp,
} from 'lucide-react'
import { CardLoadingState } from '@/components/loading-state'
import Link from 'next/link'

/* ── shared types ── */

interface AgentItem { id: number; name: string; is_default?: boolean; model_name?: string | null }
interface TopologyItem { id: number; name: string }
interface KBItem { id: number; name: string }
interface MCPItem { id: number; name: string }
interface ResourceBinding { resource_type: string; resource_id: number | string }
interface PageData<T> { items: T[]; total: number }

interface Project {
  id: number; name: string; description: string | null
  status: string; api_key: string | null; map_id: number | null
  settings: Record<string, unknown> | null
}

interface GameMapSummary {
  id: number; name: string; size_x: number; size_z: number
  status: string; source: string | null
}

/* ── root component: right-side project settings panel (General only) ── */

export function ProjectSettingsPanel({ projectId }: { projectId: string }) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">
        <GeneralSettingsTab pid={projectId} />
      </div>
    </div>
  )
}

/* ── Conversation Resource Panel (used in chat area) ── */

export interface ConversationResourceProps {
  projectId: string
  conversationId: number | string
  agentId: number | string | null | undefined
  topologyId: number | string | null | undefined
  missionObjective?: Record<string, unknown> | null
  isArma?: boolean
  onUpdated?: () => void
}

export function ConversationResourcePanel({
  projectId, conversationId, agentId, topologyId, missionObjective, isArma, onUpdated,
}: ConversationResourceProps) {
  const api = useApi()
  const { t } = useI18n()
  const queryClient = useQueryClient()

  const { data: agents } = useQuery({
    queryKey: ['agents-conv-settings'],
    queryFn: () => api.get<PageData<AgentItem>>('/agents'),
    staleTime: 30_000,
  })
  const { data: topologies } = useQuery({
    queryKey: ['topologies-conv-settings'],
    queryFn: () => api.get<PageData<TopologyItem>>('/topologies'),
    staleTime: 30_000,
  })
  const { data: kbs } = useQuery({
    queryKey: ['kbs-conv-settings'],
    queryFn: () => api.get<PageData<KBItem>>('/knowledge-bases'),
    staleTime: 30_000,
  })
  const { data: mcps } = useQuery({
    queryKey: ['mcps-conv-settings'],
    queryFn: () => api.get<PageData<MCPItem>>('/mcp-servers'),
    staleTime: 30_000,
  })
  const { data: boundResources, refetch: refetchResources } = useQuery({
    queryKey: ['conv-resources', projectId, conversationId],
    queryFn: () =>
      api.get<ResourceBinding[]>(
        `/projects/${projectId}/conversations/${conversationId}/resources`,
      ),
  })

  const updateConvMutation = useMutation({
    mutationFn: (params: { agent_id?: string | number | null; topology_id?: string | number | null; mission_objective?: Record<string, unknown> | null }) =>
      api.put(`/projects/${projectId}/conversations/${conversationId}`, params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations', projectId] })
      onUpdated?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const bindMutation = useMutation({
    mutationFn: ({ type, id }: { type: string; id: string | number }) =>
      api.post(`/projects/${projectId}/conversations/${conversationId}/resources?resource_type=${type}&resource_id=${id}`),
    onSuccess: () => { refetchResources(); toast.success(t('chat.resourceBound')) },
    onError: (err: Error) => toast.error(err.message),
  })

  const unbindMutation = useMutation({
    mutationFn: ({ type, id }: { type: string; id: string | number }) =>
      api.delete(`/projects/${projectId}/conversations/${conversationId}/resources?resource_type=${type}&resource_id=${id}`),
    onSuccess: () => { refetchResources(); toast.success(t('chat.resourceUnbound')) },
    onError: (err: Error) => toast.error(err.message),
  })

  const boundKBs = (boundResources ?? []).filter((r) => r.resource_type === 'knowledge_base')
  const boundMCPs = (boundResources ?? []).filter((r) => r.resource_type === 'mcp_server')
  const unboundKBs = (kbs?.items ?? []).filter((kb) => !boundKBs.some((b) => String(b.resource_id) === String(kb.id)))
  const unboundMCPs = (mcps?.items ?? []).filter((m) => !boundMCPs.some((b) => String(b.resource_id) === String(m.id)))

  function kbName(id: number | string) { return kbs?.items?.find((kb) => String(kb.id) === String(id))?.name ?? `#${id}` }
  function mcpName(id: number | string) { return mcps?.items?.find((m) => String(m.id) === String(id))?.name ?? `#${id}` }

  const [showResources, setShowResources] = useState(false)
  const [showMission, setShowMission] = useState(false)

  const agentName = agents?.items?.find((a) => String(a.id) === String(agentId))?.name
  const topoName = topologies?.items?.find((t) => String(t.id) === String(topologyId))?.name
  const resourceCount = boundKBs.length + boundMCPs.length
  const missionType = (missionObjective?.type as string) || 'none'

  return (
    <div className="space-y-2">
      {/* Quick summary row */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        {agentId && (
          <Badge variant="outline" className="gap-1 text-xs h-6">
            <Bot className="h-3 w-3" />{agentName ?? `#${agentId}`}
          </Badge>
        )}
        {topologyId && (
          <Badge variant="outline" className="gap-1 text-xs h-6">
            <Workflow className="h-3 w-3" />{topoName ?? `#${topologyId}`}
          </Badge>
        )}
        {resourceCount > 0 && (
          <Badge variant="outline" className="gap-1 text-xs h-6">
            <Plug className="h-3 w-3" />{resourceCount}
          </Badge>
        )}
        {isArma && missionType !== 'none' && (
          <Badge variant="outline" className="gap-1 text-xs h-6">
            {missionType}
          </Badge>
        )}
        {!agentId && !topologyId && resourceCount === 0 && (!isArma || missionType === 'none') && (
          <span className="text-muted-foreground">{t('chat.noResources')}</span>
        )}
      </div>

      {/* Resource Binding (collapsible) */}
      <div className="border rounded-md">
        <button
          onClick={() => setShowResources(!showResources)}
          className="flex items-center justify-between w-full px-3 py-2 text-xs font-medium hover:bg-muted/50 transition-colors"
        >
          <span className="flex items-center gap-1.5">
            <Settings className="h-3.5 w-3.5" />
            {t('chat.boundResources')}
          </span>
          {showResources ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>
        {showResources && (
          <div className="px-3 pb-3 space-y-3 border-t pt-2">
            {/* Agent */}
            <div className="space-y-1">
              <Label className="flex items-center gap-1 text-xs"><Bot className="h-3 w-3" />{t('chat.currentAgent')}</Label>
              <Select
                value={topologyId ? '__topo__' : (agentId ? String(agentId) : '__none__')}
                onValueChange={(v) => {
                  if (v === '__none__') updateConvMutation.mutate({ agent_id: null, topology_id: null })
                  else if (v !== '__topo__') updateConvMutation.mutate({ agent_id: v, topology_id: null })
                }}
                disabled={!!topologyId}
              >
                <SelectTrigger className="h-7 text-xs"><SelectValue placeholder={t('chat.noAgent')} /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">{t('chat.noAgent')}</SelectItem>
                  {agents?.items?.map((a) => (
                    <SelectItem key={a.id} value={String(a.id)}>{a.name}{a.is_default ? ' ★' : ''}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Topology */}
            <div className="space-y-1">
              <Label className="flex items-center gap-1 text-xs"><Workflow className="h-3 w-3" />{t('chat.currentTopology')}</Label>
              <Select
                value={topologyId ? String(topologyId) : '__none__'}
                onValueChange={(v) => {
                  if (v === '__none__') updateConvMutation.mutate({ topology_id: null })
                  else updateConvMutation.mutate({ topology_id: v, agent_id: null })
                }}
              >
                <SelectTrigger className="h-7 text-xs"><SelectValue placeholder={t('chat.noneSelected')} /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">{t('chat.noneSelected')}</SelectItem>
                  {topologies?.items?.map((tp) => (
                    <SelectItem key={tp.id} value={String(tp.id)}>{tp.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* KB */}
            <div className="space-y-1">
              <Label className="flex items-center gap-1 text-xs"><BookOpen className="h-3 w-3" />{t('chat.bindKnowledge')}</Label>
              <div className="flex flex-wrap gap-1">
                {boundKBs.map((b) => (
                  <Badge key={String(b.resource_id)} variant="secondary" className="gap-0.5 pr-0.5 text-xs h-5">
                    {kbName(b.resource_id)}
                    <button onClick={() => unbindMutation.mutate({ type: 'knowledge_base', id: b.resource_id })}
                      className="ml-0.5 rounded-full p-0.5 hover:bg-muted-foreground/20">
                      <X className="h-2.5 w-2.5" />
                    </button>
                  </Badge>
                ))}
              </div>
              {unboundKBs.length > 0 && (
                <Select value="" onValueChange={(v) => { if (v) bindMutation.mutate({ type: 'knowledge_base', id: v }) }}>
                  <SelectTrigger className="h-7 text-xs">
                    <div className="flex items-center gap-1"><Plus className="h-3 w-3" />{t('common.add')}</div>
                  </SelectTrigger>
                  <SelectContent>
                    {unboundKBs.map((kb) => (<SelectItem key={kb.id} value={String(kb.id)}>{kb.name}</SelectItem>))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {/* MCP */}
            <div className="space-y-1">
              <Label className="flex items-center gap-1 text-xs"><Plug className="h-3 w-3" />{t('chat.bindMcp')}</Label>
              <div className="flex flex-wrap gap-1">
                {boundMCPs.map((b) => (
                  <Badge key={String(b.resource_id)} variant="secondary" className="gap-0.5 pr-0.5 text-xs h-5">
                    {mcpName(b.resource_id)}
                    <button onClick={() => unbindMutation.mutate({ type: 'mcp_server', id: b.resource_id })}
                      className="ml-0.5 rounded-full p-0.5 hover:bg-muted-foreground/20">
                      <X className="h-2.5 w-2.5" />
                    </button>
                  </Badge>
                ))}
              </div>
              {unboundMCPs.length > 0 && (
                <Select value="" onValueChange={(v) => { if (v) bindMutation.mutate({ type: 'mcp_server', id: v }) }}>
                  <SelectTrigger className="h-7 text-xs">
                    <div className="flex items-center gap-1"><Plus className="h-3 w-3" />{t('common.add')}</div>
                  </SelectTrigger>
                  <SelectContent>
                    {unboundMCPs.map((m) => (<SelectItem key={m.id} value={String(m.id)}>{m.name}</SelectItem>))}
                  </SelectContent>
                </Select>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Mission Objective (collapsible, Arma only) */}
      {isArma && (
        <div className="border rounded-md">
          <button
            onClick={() => setShowMission(!showMission)}
            className="flex items-center justify-between w-full px-3 py-2 text-xs font-medium hover:bg-muted/50 transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <Crosshair className="h-3.5 w-3.5" />
              {t('arma.missionObjective')}
              {missionType !== 'none' && (
                <Badge variant="secondary" className="text-xs h-4 px-1.5">{missionType}</Badge>
              )}
            </span>
            {showMission ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
          {showMission && (
            <div className="px-3 pb-3 border-t pt-2">
              <MissionObjectiveForm
                projectId={projectId}
                conversationId={String(conversationId)}
                value={missionObjective}
                onSave={(obj) => updateConvMutation.mutate({ mission_objective: obj })}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Mission Objective Form (per-conversation) ── */

interface FocusPoint { position: number[]; label: string; radius?: number }

function MissionObjectiveForm({
  projectId, conversationId, value, onSave,
}: {
  projectId: string
  conversationId: string
  value?: Record<string, unknown> | null
  onSave: (obj: Record<string, unknown> | null) => void
}) {
  const api = useApi()
  const { t } = useI18n()
  const [missionType, setMissionType] = useState<string>((value?.type as string) || 'none')
  const [description, setDescription] = useState<string>((value?.description as string) || '')
  const [constraints, setConstraints] = useState<string>((value?.constraints as string) || '')
  const aoRaw = value?.ao as { focus_points?: FocusPoint[] } | undefined
  const [focusPoints, setFocusPoints] = useState<FocusPoint[]>(aoRaw?.focus_points || [])

  const updateFP = (idx: number, field: string, val: string | number) => {
    const updated = [...focusPoints]
    if (field === 'label') updated[idx] = { ...updated[idx], label: val as string }
    else if (field === 'x') updated[idx] = { ...updated[idx], position: [Number(val), updated[idx].position[1]] }
    else if (field === 'z') updated[idx] = { ...updated[idx], position: [updated[idx].position[0], Number(val)] }
    else if (field === 'radius') updated[idx] = { ...updated[idx], radius: Number(val) }
    setFocusPoints(updated)
  }

  const briefingMutation = useMutation({
    mutationFn: () => api.post(`/open/admin/${projectId}/generate-ao-briefing?conversation_id=${conversationId}`),
    onSuccess: () => toast.success(t('arma.aoBriefingGenerated')),
    onError: (err: Error) => toast.error(err.message),
  })

  const handleSave = () => {
    if (missionType === 'none') { onSave(null); return }
    const ao = focusPoints.length > 0 ? { focus_points: focusPoints } : undefined
    onSave({ type: missionType, description, constraints: constraints || undefined, ao })
  }

  return (
    <div className="space-y-2">
      <Label className="text-xs font-medium">{t('arma.missionObjective')}</Label>
      <select
        className="flex h-8 w-full rounded-md border bg-background px-2 py-1 text-xs"
        value={missionType}
        onChange={(e) => setMissionType(e.target.value)}
      >
        <option value="none">{t('arma.missionNone')}</option>
        <option value="attack">{t('arma.missionAttack')}</option>
        <option value="defend">{t('arma.missionDefend')}</option>
        <option value="patrol">{t('arma.missionPatrol')}</option>
        <option value="search_destroy">{t('arma.missionSearchDestroy')}</option>
        <option value="recon">{t('arma.missionRecon')}</option>
        <option value="escort">{t('arma.missionEscort')}</option>
        <option value="custom">{t('arma.missionCustom')}</option>
      </select>

      {missionType !== 'none' && (
        <div className="space-y-2">
          <div className="space-y-1">
            <Label className="text-xs">{t('arma.missionDescription')}</Label>
            <textarea
              className="flex w-full rounded-md border bg-background px-2 py-1.5 text-xs resize-y min-h-[2rem]"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g., Capture and hold the village"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">{t('arma.missionConstraints')}</Label>
            <textarea
              className="flex w-full rounded-md border bg-background px-2 py-1.5 text-xs resize-y min-h-[2rem]"
              rows={2}
              value={constraints}
              onChange={(e) => setConstraints(e.target.value)}
              placeholder="e.g., Minimize casualties"
            />
          </div>

          <div className="border rounded p-2 space-y-1.5">
            <div className="flex items-center justify-between">
              <Label className="text-xs flex items-center gap-1">{t('arma.aoConfig')}</Label>
              <Button size="sm" variant="ghost" className="h-6 text-xs px-2"
                onClick={() => setFocusPoints([...focusPoints, { position: [0, 0], label: '', radius: 1000 }])}>
                <Plus className="h-3 w-3 mr-0.5" />{t('common.add')}
              </Button>
            </div>
            {focusPoints.length === 0 && (
              <p className="text-xs text-muted-foreground">{t('arma.aoBriefingHint')}</p>
            )}
            {focusPoints.map((fp, idx) => (
              <div key={idx} className="flex items-center gap-1 bg-muted/50 rounded p-1.5">
                <Input className="basis-1/2 shrink min-w-0 h-7 text-xs" value={fp.label} onChange={(e) => updateFP(idx, 'label', e.target.value)} placeholder="Label" />
                <Input className="basis-1/4 shrink min-w-0 h-7 text-xs" type="number" value={fp.position[0]} onChange={(e) => updateFP(idx, 'x', e.target.value)} placeholder="X" />
                <Input className="basis-1/4 shrink min-w-0 h-7 text-xs" type="number" value={fp.position[1]} onChange={(e) => updateFP(idx, 'z', e.target.value)} placeholder="Z" />
                <Button size="icon" variant="ghost" className="h-6 w-6 shrink-0" onClick={() => setFocusPoints(focusPoints.filter((_, i) => i !== idx))}>
                  <Trash2 className="h-3 w-3 text-destructive" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-1.5">
        <Button size="sm" variant="outline" className="flex-1 h-7 text-xs" onClick={handleSave}>
          <Save className="h-3 w-3 mr-1" />{t('common.save')}
        </Button>
        {missionType !== 'none' && (
          <Button size="sm" variant="outline" className="flex-1 h-7 text-xs" onClick={() => briefingMutation.mutate()} disabled={briefingMutation.isPending}>
            {briefingMutation.isPending ? t('arma.generatingAoBriefing') : t('arma.generateAoBriefing')}
          </Button>
        )}
      </div>
    </div>
  )
}

/* ── General Tab ── */

function GeneralSettingsTab({ pid }: { pid: string }) {
  const api = useApi()
  const router = useRouter()
  const queryClient = useQueryClient()
  const { t } = useI18n()
  const [deleteOpen, setDeleteOpen] = useState(false)

  const { data: project, isLoading, isError } = useQuery({
    queryKey: ['project', pid],
    queryFn: () => api.get<Project>(`/projects/${pid}`),
  })

  const { data: maps } = useQuery({
    queryKey: ['maps-published'],
    queryFn: () => api.get<GameMapSummary[]>('/maps/admin/maps?status=published'),
  })

  const mapMutation = useMutation({
    mutationFn: (mapId: string | null) => api.put(`/projects/${pid}`, { map_id: mapId }),
    onSuccess: (_, mapId) => {
      queryClient.invalidateQueries({ queryKey: ['project', pid] })
      toast.success(mapId ? t('project.mapLinked') : t('project.mapUnlinked'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const updateMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.put(`/projects/${pid}`, body),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['project', pid] }); toast.success(t('project.updated')) },
    onError: (err: Error) => toast.error(err.message),
  })

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/projects/${pid}`),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['projects'] }); toast.success(t('project.deleted')); router.push('/projects') },
    onError: (err: Error) => toast.error(err.message),
  })

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    updateMutation.mutate({
      name: fd.get('name') as string,
      description: (fd.get('description') as string) || null,
      status: fd.get('status') as string,
    })
  }

  if (isLoading) return <div className="text-sm text-muted-foreground">{t('common.loading')}</div>
  if (isError) return <div className="text-sm text-destructive">{t('error.loadFailed')}</div>
  if (!project) return <div className="text-sm">{t('project.notFound')}</div>

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="name">{t('project.projectName')}</Label>
          <Input id="name" name="name" required defaultValue={project.name} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="description">{t('project.description')}</Label>
          <Textarea id="description" name="description" rows={3} defaultValue={project.description ?? ''} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="status">{t('common.status')}</Label>
          <select id="status" name="status" defaultValue={project.status}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
            <option value="active">{t('project.statusActive')}</option>
            <option value="archived">{t('project.statusArchived')}</option>
          </select>
        </div>
        <Button type="submit" className="w-full" disabled={updateMutation.isPending}>
          {updateMutation.isPending ? t('common.saving') : t('common.save')}
        </Button>
      </form>

      <Separator />

      {/* Map Selection */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium flex items-center gap-2">
          <Map className="h-4 w-4" />
          {t('project.selectMap')}
        </h3>
        <select
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
          value={String(project.map_id ?? '')}
          onChange={(e) => mapMutation.mutate(e.target.value || null)}
        >
          <option value="">{t('project.noMapSelected')}</option>
          {(maps || []).map((m) => (
            <option key={String(m.id)} value={String(m.id)}>
              {m.name} ({m.size_x} × {m.size_z} m)
            </option>
          ))}
        </select>
        {(() => {
          const currentMap = (maps || []).find((m) => String(m.id) === String(project.map_id))
          return currentMap ? (
            <div className="p-3 rounded-lg border bg-muted/30 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm">{currentMap.name}</span>
                <Badge variant="default" className="text-xs">{currentMap.status}</Badge>
              </div>
              <p className="text-xs text-muted-foreground">{currentMap.size_x}m × {currentMap.size_z}m</p>
            </div>
          ) : null
        })()}
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{t('project.manageMapHint')}</span>
          <Link href="/maps">
            <Button size="sm" variant="outline">
              <ExternalLink className="h-4 w-4 mr-1" />
              {t('mapAdmin.title')}
            </Button>
          </Link>
        </div>
      </div>

      <Separator />

      <div>
        <h3 className="text-sm font-semibold text-destructive mb-1">{t('project.dangerZone')}</h3>
        <p className="text-xs text-muted-foreground mb-3">{t('project.dangerHint')}</p>
        <Button variant="destructive" size="sm" onClick={() => setDeleteOpen(true)}>
          {t('project.deleteProject')}
        </Button>
      </div>

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('error.confirmDelete')}</AlertDialogTitle>
            <AlertDialogDescription>{t('project.confirmDeleteProject', { name: project.name })}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteMutation.mutate()}>{t('common.delete')}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

/* ── Map Tab ── */

/* ── Arma Tab ── */

interface SideConfigItem { faction: string; control: string }

interface ArmaConfig {
  id: number; project_id: number; conversation_group_id: number | null
  enabled: boolean; running: boolean
  sides: SideConfigItem[]; decision_interval: number; max_squads: number
  emergency_enabled: boolean; game_mode: string; language: string
  context_window: number
}

interface CommandEntry {
  id: string; conversation_id: string; request_id: number; status: string
  orders_json: Record<string, unknown> | null; delivered_at: string | null; created_time: string | null
}

interface LogEntry {
  id: string; conversation_id: string; request_id: number; priority: string
  situation_json: Record<string, unknown> | null; response_json: Record<string, unknown> | null
  processing_time_ms: number | null; created_time: string | null
}

interface ListResult<T> { items: T[]; total: number }

interface SituationData {
  request_id: number; timestamp: number | null
  game_state: Record<string, string>
  llm_groups: GroupInfo[]; other_groups: GroupInfo[]
  total_groups: number; pending_commands: number
  last_processing_time_ms: number | null
  last_orders: { orders?: OrderInfo[]; briefing?: string; assessment?: string } | null
  updated_at: string | null
}

interface GroupInfo {
  id: string; label: string; description?: string; faction: string; control: string
  role: string; position: number[]; member_count: number; casualties: number
  current_waypoint_type: string; combat_mode: string; speed_mode?: string
  in_vehicle?: boolean; leader_stance?: string
  known_enemies?: {
    position: number[]; detected_position?: number[]; distance?: number
    time_since_seen: number; time_since_detected?: number; time_since_side_recognized?: number
    time_since_type_recognized?: number; time_since_endangered?: number
    unit_type?: string; is_disarmed?: boolean; trace_fraction?: number
    perceived_faction?: string; identified?: boolean; endangering?: boolean
  }[]
  environment?: { elevation: number }
}

interface OrderInfo { type: string; group_id: string; target?: number[]; speed?: string; mode?: string }

const FACTIONS = ['US', 'USSR', 'FIA', 'CIV', 'RHS_USAF', 'RHS_AFRF', 'RHS_ION', 'MEI', 'MEC'] as const
const CONTROLS = ['human', 'llm'] as const
const GAME_MODES = ['game_master', 'conflict'] as const
const LANGUAGES_LIST = ['en', 'zh'] as const

function CollapsibleSection({
  title, icon, defaultOpen = false, badge, children,
}: {
  title: string; icon: React.ReactNode; defaultOpen?: boolean; badge?: React.ReactNode; children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div>
      <button onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full py-2 text-sm font-medium hover:text-foreground transition-colors">
        <span className="flex items-center gap-2">{icon}{title}{badge}</span>
        {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>
      {open && <div className="pb-2">{children}</div>}
    </div>
  )
}

export function ArmaSettingsTab({
  pid, groupId, conversationId,
}: {
  pid: string; groupId?: number | string | null; conversationId?: number | string | null
}) {
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()

  const gidParam = groupId ? `?group_id=${groupId}` : ''
  const { data: config, isLoading } = useQuery({
    queryKey: ['arma-config', pid, groupId],
    queryFn: () => api.get<ArmaConfig | null>(`/open/admin/${pid}/arma-config${gidParam}`),
  })
  const { data: projectMeta } = useQuery({
    queryKey: ['project', pid],
    queryFn: () => api.get<Project>(`/projects/${pid}`),
  })

  const createMutation = useMutation({
    mutationFn: () => {
      const convParam = conversationId ? `?conversation_id=${conversationId}` : ''
      return api.post(`/open/admin/${pid}/arma-config${convParam}`, {})
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['arma-config'] })
      queryClient.invalidateQueries({ queryKey: ['conversations', pid] })
      queryClient.invalidateQueries({ queryKey: ['conv-detail', pid] })
      toast.success(t('common.saved'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  if (isLoading) return <CardLoadingState />

  if (!config) {
    return (
      <div className="space-y-3 text-center py-4">
        <Swords className="h-8 w-8 mx-auto text-muted-foreground" />
        <p className="text-sm text-muted-foreground">{t('arma.noConfig')}</p>
        <Button
          size="sm"
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
        >
          <Swords className="h-4 w-4 mr-1" />
          {t('project.enableArma')}
        </Button>
      </div>
    )
  }

  const effectiveGroupId = groupId || config.conversation_group_id

  return (
    <div className="divide-y">
      <CollapsibleSection title={t('arma.factionConfig')} icon={<Swords className="h-4 w-4" />} defaultOpen>
        <ArmaFactionSection pid={pid} config={config} groupId={effectiveGroupId} />
      </CollapsibleSection>

      <CollapsibleSection title={t('arma.gameSettings')} icon={<Settings className="h-4 w-4" />}>
        <ArmaGameSection pid={pid} config={config} groupId={effectiveGroupId} />
      </CollapsibleSection>

      <CollapsibleSection title={t('arma.runControl')} icon={<Play className="h-4 w-4" />} defaultOpen
        badge={
          <span className={`ml-1 h-2 w-2 rounded-full inline-block ${config.running ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`} />
        }>
        <ArmaRunSection pid={pid} config={config} groupId={effectiveGroupId} />
      </CollapsibleSection>

      {config.running && (
        <CollapsibleSection title={t('arma.situationPanel') || 'Situation'} icon={<Activity className="h-4 w-4" />} defaultOpen>
          <ArmaSituationSection pid={pid} />
        </CollapsibleSection>
      )}

      <CollapsibleSection title={t('openApi.apiKeyTitle')} icon={<Copy className="h-4 w-4" />}>
        <ArmaApiKeySection pid={pid} apiKey={projectMeta?.api_key ?? null} />
      </CollapsibleSection>

      <CollapsibleSection title={t('openApi.commandPool')} icon={<Clock className="h-4 w-4" />}>
        <ArmaRuntimeSection pid={pid} groupId={effectiveGroupId} />
      </CollapsibleSection>
    </div>
  )
}

function ArmaFactionSection({ pid, config, groupId }: { pid: string; config: ArmaConfig; groupId?: number | string | null }) {
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()

  const gidParam = groupId ? `?group_id=${groupId}` : ''
  const defaultSides: SideConfigItem[] = config.sides?.length
    ? config.sides : [{ faction: 'US', control: 'human' }, { faction: 'USSR', control: 'llm' }]
  const [sides, setSides] = useState<SideConfigItem[]>(defaultSides)

  const updateMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.put(`/open/admin/${pid}/arma-config${gidParam}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['arma-config', pid, groupId] })
      queryClient.invalidateQueries({ queryKey: ['arma-config', pid] })
      queryClient.invalidateQueries({ queryKey: ['conversations', pid] })
      queryClient.invalidateQueries({ queryKey: ['conv-detail', pid] })
      toast.success(t('common.saved'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  function addSide() {
    const used = new Set(sides.map((s) => s.faction))
    setSides([...sides, { faction: FACTIONS.find((f) => !used.has(f)) || 'US', control: 'llm' }])
  }

  function updateSide(idx: number, field: 'faction' | 'control', value: string) {
    const updated = [...sides]; updated[idx] = { ...updated[idx], [field]: value }; setSides(updated)
  }

  const factionColors: Record<string, string> = {
    US: 'border-blue-500/50 bg-blue-500/5',
    USSR: 'border-red-500/50 bg-red-500/5',
    FIA: 'border-green-500/50 bg-green-500/5',
    CIV: 'border-purple-500/50 bg-purple-500/5',
    RHS_USAF: 'border-blue-400/50 bg-blue-400/5',
    RHS_AFRF: 'border-red-700/50 bg-red-700/5',
    RHS_ION: 'border-green-400/50 bg-green-400/5',
    MEI: 'border-yellow-600/50 bg-yellow-600/5',
    MEC: 'border-purple-400/50 bg-purple-400/5',
  }

  return (
    <div className="space-y-3">
      {sides.map((side, idx) => (
        <div key={idx} className={`p-3 rounded-lg border-2 space-y-2 ${factionColors[side.faction] || 'border-border'}`}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{t('arma.side')} {idx + 1}</span>
            {sides.length > 1 && (
              <Button size="icon" variant="ghost" className="h-6 w-6"
                onClick={() => { if (sides.length > 1) setSides(sides.filter((_, i) => i !== idx)) }}>
                <Trash2 className="h-3.5 w-3.5 text-destructive" />
              </Button>
            )}
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">{t('arma.faction')}</Label>
            <select value={side.faction} onChange={(e) => updateSide(idx, 'faction', e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
              {FACTIONS.map((f) => <option key={f} value={f}>{t(`arma.faction_${f}`)}</option>)}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">{t('arma.control')}</Label>
            <select value={side.control} onChange={(e) => updateSide(idx, 'control', e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
              {CONTROLS.map((c) => <option key={c} value={c}>{t(`arma.control_${c}`)}</option>)}
            </select>
          </div>
        </div>
      ))}

      <div className="flex gap-2">
        {sides.length < FACTIONS.length && (
          <Button size="sm" variant="outline" className="flex-1" onClick={addSide}>
            <Plus className="h-4 w-4 mr-1" />{t('arma.addSide')}
          </Button>
        )}
        <Button size="sm" className="flex-1" onClick={() => updateMutation.mutate({ sides })} disabled={updateMutation.isPending}>
          <Save className="h-4 w-4 mr-1" />{t('common.save')}
        </Button>
      </div>
    </div>
  )
}

function ArmaGameSection({ pid, config, groupId }: { pid: string; config: ArmaConfig; groupId?: number | string | null }) {
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()

  const gidParam = groupId ? `?group_id=${groupId}` : ''
  const [interval, setInterval_] = useState(config.decision_interval)
  const [maxSquads, setMaxSquads] = useState(config.max_squads)
  const [emergency, setEmergency] = useState(config.emergency_enabled)
  const [gameMode, setGameMode] = useState(config.game_mode)
  const [language, setLanguage] = useState(config.language)
  const [contextWindow, setContextWindow] = useState(config.context_window ?? 15)

  const updateMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.put(`/open/admin/${pid}/arma-config${gidParam}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['arma-config', pid, groupId] })
      queryClient.invalidateQueries({ queryKey: ['arma-config', pid] })
      toast.success(t('common.saved'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label>{t('arma.decisionInterval')}</Label>
        <div className="flex items-center gap-2">
          <Input type="number" min={5} max={300} step={5} value={interval}
            onChange={(e) => setInterval_(parseFloat(e.target.value) || 30)} className="w-24" />
          <span className="text-xs text-muted-foreground">{t('arma.seconds')}</span>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label>{t('arma.maxSquads')}</Label>
        <Input type="number" min={1} max={50} value={maxSquads}
          onChange={(e) => setMaxSquads(parseInt(e.target.value) || 12)} className="w-24" />
      </div>

      <div className="space-y-1.5">
        <Label>{t('arma.gameMode')}</Label>
        <select value={gameMode} onChange={(e) => setGameMode(e.target.value)}
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
          {GAME_MODES.map((m) => <option key={m} value={m}>{t(`arma.gameMode_${m}`)}</option>)}
        </select>
      </div>

      <div className="space-y-1.5">
        <Label>{t('arma.aiLanguage')}</Label>
        <select value={language} onChange={(e) => setLanguage(e.target.value)}
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
          {LANGUAGES_LIST.map((l) => <option key={l} value={l}>{t(`arma.language_${l}`)}</option>)}
        </select>
      </div>

      <div className="flex items-center justify-between rounded-md border p-3">
        <div>
          <span className="text-sm font-medium">{t('arma.emergencyDetection')}</span>
          <p className="text-xs text-muted-foreground">{t('arma.emergencyDesc')}</p>
        </div>
        <input type="checkbox" checked={emergency} onChange={(e) => setEmergency(e.target.checked)}
          className="rounded border-input h-4 w-4" />
      </div>

      <div className="space-y-1.5">
        <Label>{t('arma.contextWindow')}</Label>
        <div className="flex items-center gap-2">
          <Input type="number" min={5} max={100} step={5} value={contextWindow}
            onChange={(e) => setContextWindow(Number(e.target.value))} className="w-24" />
          <span className="text-xs text-muted-foreground">reports</span>
        </div>
        <p className="text-xs text-muted-foreground">{t('arma.contextWindowDesc')}</p>
      </div>

      <Button className="w-full" onClick={() => updateMutation.mutate({
        decision_interval: interval, max_squads: maxSquads, emergency_enabled: emergency,
        game_mode: gameMode, language, context_window: contextWindow,
      })} disabled={updateMutation.isPending}>
        <Save className="h-4 w-4 mr-1" />{t('common.save')}
      </Button>
    </div>
  )
}

function ArmaRunSection({ pid, config, groupId }: { pid: string; config: ArmaConfig; groupId?: number | string | null }) {
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()

  const gidParam = groupId ? `?group_id=${groupId}` : ''
  const updateMutation = useMutation({
    mutationFn: (running: boolean) => api.put(`/open/admin/${pid}/arma-config${gidParam}`, { running }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['arma-config', pid, groupId] })
      queryClient.invalidateQueries({ queryKey: ['arma-config', pid] })
      queryClient.invalidateQueries({ queryKey: ['arma-configs', pid] })
    },
    onError: (err: Error) => toast.error(err.message),
  })

  return (
    <div className="flex items-center justify-between">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <div className={`h-3 w-3 rounded-full ${config.running ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`} />
          <span className="font-medium text-sm">{config.running ? t('arma.statusRunning') : t('arma.statusIdle')}</span>
        </div>
        <p className="text-xs text-muted-foreground">{t('arma.runControlDesc')}</p>
      </div>
      {config.running ? (
        <Button variant="destructive" size="sm" onClick={() => updateMutation.mutate(false)} disabled={updateMutation.isPending}>
          <Square className="h-4 w-4 mr-1" />{t('arma.stop')}
        </Button>
      ) : (
        <Button size="sm" onClick={() => updateMutation.mutate(true)} disabled={updateMutation.isPending}>
          <Play className="h-4 w-4 mr-1" />{t('arma.start')}
        </Button>
      )}
    </div>
  )
}

function ArmaSituationSection({ pid }: { pid: string }) {
  const api = useApi()
  const { t } = useI18n()
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null)

  const { data: situation } = useQuery({
    queryKey: ['arma-situation', pid],
    queryFn: () => api.get<SituationData | null>(`/open/admin/${pid}/situation`),
    refetchInterval: 10_000,
  })

  if (!situation) return <p className="text-sm text-muted-foreground">{t('arma.noSituation') || 'Waiting for data...'}</p>

  const controlColor: Record<string, string> = {
    llm: 'bg-blue-500/10 text-blue-600 border-blue-500/20',
    human: 'bg-amber-500/10 text-amber-600 border-amber-500/20',
  }
  const orderTypeColor: Record<string, string> = {
    move: 'bg-green-500/10 text-green-600', patrol: 'bg-blue-500/10 text-blue-600',
    defend: 'bg-amber-500/10 text-amber-600', attack: 'bg-red-500/10 text-red-600',
    hold: 'bg-gray-500/10 text-gray-600', retreat: 'bg-orange-500/10 text-orange-600',
  }

  const allGroups = [...situation.llm_groups, ...situation.other_groups]
  const orders = situation.last_orders?.orders || []

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span>#{situation.request_id}</span>
        {situation.last_processing_time_ms != null && (
          <span>{(situation.last_processing_time_ms / 1000).toFixed(1)}s</span>
        )}
        {situation.pending_commands > 0 && (
          <Badge variant="outline" className="text-xs bg-yellow-500/10 text-yellow-600">
            {situation.pending_commands} pending
          </Badge>
        )}
      </div>

      {situation.last_orders?.briefing && (
        <div className="rounded-lg bg-muted/50 p-3">
          <p className="text-xs font-medium text-muted-foreground mb-1">Briefing</p>
          <p className="text-sm">{situation.last_orders.briefing}</p>
        </div>
      )}

      <p className="text-xs text-muted-foreground flex items-center gap-1">
        <Users className="h-3.5 w-3.5" />
        {situation.llm_groups.length} AI / {situation.other_groups.length} human
      </p>

      <div className="space-y-1.5">
        {allGroups.map((g) => {
          const isExpanded = expandedGroup === g.id
          const groupOrder = orders.find((o) => o.group_id === g.id)
          const enemies = g.known_enemies || []
          return (
            <div key={g.id} className="rounded-lg border p-2.5 cursor-pointer hover:bg-muted/30 transition-colors"
              onClick={() => setExpandedGroup(isExpanded ? null : g.id)}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 min-w-0">
                  <Badge variant="outline" className={`text-xs ${controlColor[g.control] || ''}`}>{g.control}</Badge>
                  <span className="text-sm font-medium truncate">{g.label}</span>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {enemies.length > 0 && (
                    <Badge variant="outline" className="text-xs bg-red-500/10 text-red-600">
                      <Crosshair className="h-3 w-3 mr-0.5" />{enemies.length}
                    </Badge>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {g.member_count}{g.casualties > 0 && <span className="text-red-500"> -{g.casualties}</span>}
                  </span>
                  {groupOrder && <Badge className={`text-xs ${orderTypeColor[groupOrder.type] || ''}`}>{groupOrder.type}</Badge>}
                </div>
              </div>
              {isExpanded && (
                <div className="mt-2 pt-2 border-t text-xs space-y-1 text-muted-foreground">
                  <p>Faction: {g.faction} | Role: {g.role}</p>
                  <p>Orders: {g.current_waypoint_type} | Combat: {g.combat_mode}</p>
                  {g.position && <p>Pos: [{g.position.map((v) => Math.round(v)).join(', ')}]</p>}
                  {enemies.length > 0 && (
                    <div>
                      <p className="font-medium text-red-500">Contacts:</p>
                      {enemies.slice(0, 3).map((e, i) => (
                        <p key={i}>
                          [{e.position?.map((v: number) => Math.round(v)).join(', ')}]
                          {e.distance != null && e.distance >= 0 ? ` ${Math.round(e.distance)}m` : ''}
                          {' '}{e.time_since_seen?.toFixed(0)}s ago
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ArmaApiKeySection({ pid, apiKey }: { pid: string; apiKey: string | null }) {
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()

  const regenMutation = useMutation({
    mutationFn: () => api.post<{ api_key: string }>(`/open/admin/${pid}/regenerate-key`),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['project', pid] }); toast.success(t('openApi.keyRegenerated')) },
    onError: (err: Error) => toast.error(err.message),
  })

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">{t('openApi.apiKeyDesc')}</p>
      {apiKey ? (
        <div className="flex items-center gap-2">
          <code className="flex-1 text-xs bg-muted px-3 py-2 rounded-md break-all font-mono">{apiKey}</code>
          <Button variant="outline" size="icon" className="shrink-0"
            onClick={() => { navigator.clipboard.writeText(apiKey); toast.success(t('openApi.keyCopied')) }}>
            <Copy className="h-4 w-4" />
          </Button>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground italic">{t('openApi.noKey')}</p>
      )}
      <Button variant="outline" size="sm" className="w-full" onClick={() => regenMutation.mutate()} disabled={regenMutation.isPending}>
        <RefreshCw className={`h-4 w-4 mr-1 ${regenMutation.isPending ? 'animate-spin' : ''}`} />
        {apiKey ? t('openApi.regenerateKey') : t('openApi.generateKey')}
      </Button>
    </div>
  )
}

function ArmaRuntimeSection({ pid, groupId }: { pid: string; groupId?: number | string | null }) {
  const api = useApi()
  const { t } = useI18n()
  const [expandedCmd, setExpandedCmd] = useState<string | null>(null)
  const [expandedLog, setExpandedLog] = useState<string | null>(null)

  const groupParam = groupId ? `&group_id=${groupId}` : ''
  const { data: commands, isLoading: cmdLoading } = useQuery({
    queryKey: ['open-commands', pid, groupId],
    queryFn: () => api.get<ListResult<CommandEntry>>(`/open/admin/${pid}/commands?limit=10${groupParam}`),
    refetchInterval: 10_000,
  })

  const { data: logs, isLoading: logLoading } = useQuery({
    queryKey: ['open-logs', pid, groupId],
    queryFn: () => api.get<ListResult<LogEntry>>(`/open/admin/${pid}/logs?limit=10${groupParam}`),
    refetchInterval: 10_000,
  })

  const statusColor: Record<string, string> = {
    pending: 'bg-yellow-500/10 text-yellow-600',
    delivered: 'bg-green-500/10 text-green-600',
    expired: 'bg-red-500/10 text-red-600',
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm font-medium mb-2">{t('openApi.commandPool')}</p>
        {cmdLoading ? (
          <p className="text-sm text-muted-foreground">{t('common.loading')}</p>
        ) : !commands?.items?.length ? (
          <p className="text-sm text-muted-foreground">{t('openApi.noCommands')}</p>
        ) : (
          <div className="space-y-1.5">
            {commands.items.map((cmd) => (
              <div key={cmd.id} className="border rounded-md p-2.5 text-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={statusColor[cmd.status] || ''}>{cmd.status}</Badge>
                    <span className="text-xs text-muted-foreground">#{cmd.request_id}</span>
                  </div>
                  <Button variant="ghost" size="icon" className="h-6 w-6"
                    onClick={() => setExpandedCmd(expandedCmd === cmd.id ? null : cmd.id)}>
                    {expandedCmd === cmd.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </Button>
                </div>
                {expandedCmd === cmd.id && cmd.orders_json && (
                  <pre className="mt-2 text-xs bg-muted p-2 rounded overflow-auto max-h-48">
                    {JSON.stringify(cmd.orders_json, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <p className="text-sm font-medium mb-2">{t('openApi.situationLogs')}</p>
        {logLoading ? (
          <p className="text-sm text-muted-foreground">{t('common.loading')}</p>
        ) : !logs?.items?.length ? (
          <p className="text-sm text-muted-foreground">{t('openApi.noLogs')}</p>
        ) : (
          <div className="space-y-1.5">
            {logs.items.map((log) => (
              <div key={log.id} className="border rounded-md p-2.5 text-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={log.priority === 'urgent' ? 'bg-red-500/10 text-red-600' : ''}>
                      {log.priority}
                    </Badge>
                    <span className="text-xs text-muted-foreground">#{log.request_id}</span>
                  </div>
                  <Button variant="ghost" size="icon" className="h-6 w-6"
                    onClick={() => setExpandedLog(expandedLog === log.id ? null : log.id)}>
                    {expandedLog === log.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </Button>
                </div>
                {expandedLog === log.id && log.response_json && (
                  <pre className="mt-2 text-xs bg-muted p-2 rounded overflow-auto max-h-48">
                    {JSON.stringify(log.response_json, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
