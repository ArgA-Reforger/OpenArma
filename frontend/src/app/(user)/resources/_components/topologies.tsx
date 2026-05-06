'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { Copy, Workflow, Bot } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import dynamic from 'next/dynamic'
import { useResourceCRUD } from '@/hooks/use-resource-crud'
import { DeleteConfirmDialog } from '@/components/resource/delete-confirm-dialog'
import type { EmbeddedProps, PageData } from '@/types/resources'
import type { TopologyData } from '../../projects/[id]/settings/topology/topology-editor'

const TopologyEditor = dynamic(
  () => import('../../projects/[id]/settings/topology/topology-editor'),
  { ssr: false },
)

interface SimpleAgent {
  id: number
  name: string
  model_name: string | null
}

type TopoTemplate = 'sequential' | 'parallel' | 'coordinator'

function generateTopology(agents: SimpleAgent[], template: TopoTemplate): TopologyData {
  if (agents.length === 0) return { nodes: [], edges: [] }
  const spacing = 250
  const nodes: TopologyData['nodes'] = []
  const edges: TopologyData['edges'] = []

  if (template === 'sequential') {
    agents.forEach((a, i) => {
      const id = `agent_${a.id}`
      nodes.push({ id, type: 'agent', agent_id: a.id, config: { label: a.name, agent_name: a.name, model_name: a.model_name || '' }, position: { x: 100 + i * spacing, y: 200 } })
      if (i > 0) edges.push({ id: `e_${i}`, source: `agent_${agents[i - 1].id}`, target: id, config: {} })
    })
  } else if (template === 'parallel') {
    const aggId = 'aggregator_1'
    agents.forEach((a, i) => {
      const id = `agent_${a.id}`
      nodes.push({ id, type: 'agent', agent_id: a.id, config: { label: a.name, agent_name: a.name, model_name: a.model_name || '' }, position: { x: 100 + i * spacing, y: 100 } })
      edges.push({ id: `e_${i}`, source: id, target: aggId, config: {} })
    })
    nodes.push({ id: aggId, type: 'aggregator', config: { label: 'Aggregator', merge_strategy: 'aggregator' }, position: { x: 100 + ((agents.length - 1) * spacing) / 2, y: 350 } })
  } else {
    const coordId = 'coordinator_1'
    const aggId = 'aggregator_1'
    nodes.push({ id: coordId, type: 'coordinator', config: { label: 'Coordinator', merge_strategy: 'coordinator' }, position: { x: 100 + ((agents.length - 1) * spacing) / 2, y: 50 } })
    agents.forEach((a, i) => {
      const id = `agent_${a.id}`
      nodes.push({ id, type: 'agent', agent_id: a.id, config: { label: a.name, agent_name: a.name, model_name: a.model_name || '' }, position: { x: 100 + i * spacing, y: 250 } })
      edges.push({ id: `ec_${i}`, source: coordId, target: id, config: {} })
      edges.push({ id: `ea_${i}`, source: id, target: aggId, config: {} })
    })
    nodes.push({ id: aggId, type: 'aggregator', config: { label: 'Aggregator', merge_strategy: 'aggregator' }, position: { x: 100 + ((agents.length - 1) * spacing) / 2, y: 450 } })
  }
  return { nodes, edges }
}

interface Topology {
  id: number
  name: string
  description: string | null
  topology_json: Record<string, unknown> | null
  visibility: string
  user_id: number
  created_time: string
  updated_time: string | null
}

export function TopologiesPage({ embedded, addDialogOpen, onAddDialogOpenChange }: EmbeddedProps = {}) {
  const api = useApi()
  const { t } = useI18n()
  const [internalOpen, setInternalOpen] = useState(false)
  const open = addDialogOpen ?? internalOpen
  const setOpen = onAddDialogOpenChange ?? setInternalOpen
  const [editTarget, setEditTarget] = useState<Topology | null>(null)
  const [editOpen, setEditOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Topology | null>(null)
  const [designTarget, setDesignTarget] = useState<Topology | null>(null)
  const [selectedAgents, setSelectedAgents] = useState<Set<number>>(new Set())
  const [topoTemplate, setTopoTemplate] = useState<TopoTemplate>('sequential')

  const {
    items, isLoading, isError, invalidate,
    createMutation, updateMutation, deleteMutation, cloneMutation,
  } = useResourceCRUD<Topology>({
    endpoint: '/topologies',
    queryKey: ['topologies'],
    toastKeys: { created: 'topology.created', deleted: 'topology.deleted', cloned: 'topology.cloned' },
  })

  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: () => api.get<PageData<SimpleAgent>>('/agents'),
  })

  function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const agents = (agentsData?.items ?? []).filter((a) => selectedAgents.has(a.id))
    const topoJson = agents.length > 0 ? generateTopology(agents, topoTemplate) : null
    createMutation.mutate({
      name: fd.get('name') as string,
      description: (fd.get('description') as string) || null,
      visibility: fd.get('visibility') as string,
      topology_json: topoJson,
    }, { onSuccess: () => { setOpen(false); setSelectedAgents(new Set()); setTopoTemplate('sequential') } })
  }

  function handleUpdate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!editTarget) return
    const fd = new FormData(e.currentTarget)
    updateMutation.mutate({
      id: editTarget.id,
      body: {
        name: fd.get('name') as string,
        description: (fd.get('description') as string) || null,
        visibility: fd.get('visibility') as string,
      },
    }, { onSuccess: () => { setEditOpen(false); setEditTarget(null); toast.success(t('common.saved')) } })
  }

  function nodeCount(topo: Topology): number {
    const json = topo.topology_json as { nodes?: unknown[] } | null
    return json?.nodes?.length ?? 0
  }

  const content = (
    <>
      {!embedded && (
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">{t('topology.title')}</h1>
          <Button onClick={() => setOpen(true)}>{t('topology.create')}</Button>
        </div>
      )}

      {isLoading && <p className="text-muted-foreground text-sm p-4">{t('common.loading')}</p>}
      {isError && <p className="text-destructive text-sm p-4">{t('common.loadError')}</p>}
      {!isLoading && !isError && items.length === 0 && (
        <p className="text-muted-foreground text-sm p-4">{t('topology.empty')}</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((topo) => (
          <Card key={topo.id} className="cursor-pointer hover:bg-accent/50 transition-colors" onClick={() => { setEditTarget(topo); setEditOpen(true) }}>
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="text-base leading-snug">{topo.name}</CardTitle>
                <Badge variant={topo.visibility === 'official' ? 'default' : 'secondary'} className="shrink-0 text-[10px]">{topo.visibility}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {topo.description && <p className="text-xs text-muted-foreground line-clamp-2">{topo.description}</p>}
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{nodeCount(topo)} {t('topology.nodes')}</span>
                <span>·</span>
                <span>{new Date(topo.created_time).toLocaleDateString()}</span>
              </div>
              <div className="flex items-center gap-1.5 pt-1" onClick={(e) => e.stopPropagation()}>
                <Button size="sm" variant="default" className="h-7 text-xs gap-1" onClick={() => setDesignTarget(topo)}>
                  <Workflow className="h-3 w-3" />
                  {t('topology.design')}
                </Button>
                <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => cloneMutation.mutate(topo.id)}>
                  <Copy className="h-3 w-3 mr-1" />
                  {t('common.clone')}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) { setSelectedAgents(new Set()); setTopoTemplate('sequential') } }}>
        <DialogContent className="max-h-[85vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{t('topology.create')}</DialogTitle></DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label>{t('topology.name')}</Label>
              <Input name="name" required placeholder={t('topology.namePlaceholder')} />
            </div>
            <div className="space-y-2">
              <Label>{t('topology.description')}</Label>
              <Textarea name="description" rows={2} placeholder={t('topology.descriptionPlaceholder')} />
            </div>
            <div className="space-y-2">
              <Label>{t('topology.visibility')}</Label>
              <Select name="visibility" defaultValue="private">
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="private">{t('common.private')}</SelectItem>
                  <SelectItem value="public">{t('common.public')}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>{t('topology.selectAgents')}</Label>
              <div className="rounded-md border max-h-48 overflow-y-auto divide-y">
                {(agentsData?.items ?? []).map((a) => {
                  const checked = selectedAgents.has(a.id)
                  return (
                    <label key={a.id} className="flex items-center gap-3 px-3 py-2 hover:bg-accent/50 cursor-pointer">
                      <input type="checkbox" className="rounded border-input h-4 w-4 shrink-0" checked={checked} onChange={() => { const next = new Set(selectedAgents); if (checked) next.delete(a.id); else next.add(a.id); setSelectedAgents(next) }} />
                      <Bot className="h-4 w-4 text-muted-foreground shrink-0" />
                      <span className="text-sm flex-1 truncate">{a.name}</span>
                      {a.model_name && <span className="text-xs text-muted-foreground">{a.model_name}</span>}
                    </label>
                  )
                })}
                {(agentsData?.items ?? []).length === 0 && (
                  <div className="px-3 py-4 text-sm text-muted-foreground text-center">{t('topology.noAgents')}</div>
                )}
              </div>
              <p className="text-xs text-muted-foreground">{t('topology.selectAgentsHint')}</p>
            </div>
            {selectedAgents.size > 0 && (
              <div className="space-y-2">
                <Label>{t('topology.templateLabel')}</Label>
                <div className="grid grid-cols-3 gap-2">
                  {(['sequential', 'parallel', 'coordinator'] as const).map((tpl) => (
                    <button key={tpl} type="button" onClick={() => setTopoTemplate(tpl)} className={cn('rounded-md border px-3 py-2 text-xs font-medium transition-colors', topoTemplate === tpl ? 'border-primary bg-primary/10 text-primary' : 'hover:bg-accent')}>
                      {t(`topology.template_${tpl}`)}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <Button type="submit" className="w-full" disabled={createMutation.isPending}>{t('common.create')}</Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={editOpen} onOpenChange={(v) => { setEditOpen(v); if (!v) setEditTarget(null) }}>
        <DialogContent>
          <DialogHeader><DialogTitle>{t('topology.edit')}</DialogTitle></DialogHeader>
          {editTarget && (
            <form onSubmit={handleUpdate} className="space-y-4">
              <div className="space-y-2">
                <Label>{t('topology.name')}</Label>
                <Input name="name" required defaultValue={editTarget.name} />
              </div>
              <div className="space-y-2">
                <Label>{t('topology.description')}</Label>
                <Textarea name="description" rows={2} defaultValue={editTarget.description ?? ''} />
              </div>
              <div className="space-y-2">
                <Label>{t('topology.visibility')}</Label>
                <Select name="visibility" defaultValue={editTarget.visibility}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="private">{t('common.private')}</SelectItem>
                    <SelectItem value="public">{t('common.public')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex gap-2">
                <Button type="submit" className="flex-1" disabled={updateMutation.isPending}>{t('common.save')}</Button>
                <Button type="button" variant="destructive" onClick={() => setDeleteTarget(editTarget)}>{t('common.delete')}</Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>

      <DeleteConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(v) => { if (!v) setDeleteTarget(null) }}
        itemName={deleteTarget?.name ?? ''}
        titleKey="common.confirmDelete"
        descriptionKey="topology.confirmDelete"
        onConfirm={() => { if (deleteTarget) { deleteMutation.mutate(deleteTarget.id); setEditOpen(false); setEditTarget(null) } }}
      />

      <Dialog open={!!designTarget} onOpenChange={(v) => { if (!v) setDesignTarget(null) }}>
        <DialogContent className="max-w-[95vw] sm:max-w-[95vw] w-[95vw] h-[90vh] max-h-[90vh] flex flex-col p-0 gap-0">
          <DialogHeader className="px-6 pt-4 pb-2 shrink-0">
            <DialogTitle>{designTarget?.name} — {t('topology.design')}</DialogTitle>
          </DialogHeader>
          <div className="flex-1 min-h-0 px-4 pb-4 overflow-hidden">
            {designTarget && (
              <TopologyEditor
                initialTopology={designTarget.topology_json as TopologyData | null}
                onSave={async (topo) => {
                  try {
                    await api.put(`/topologies/${designTarget.id}`, { topology_json: topo })
                    invalidate()
                    toast.success(t('common.saved'))
                    setDesignTarget(null)
                  } catch {
                    toast.error(t('common.error'))
                  }
                }}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )

  return embedded ? <div className="p-4">{content}</div> : <div className="p-6">{content}</div>
}
