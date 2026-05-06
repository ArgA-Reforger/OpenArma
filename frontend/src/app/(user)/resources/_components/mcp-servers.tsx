'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { Copy } from 'lucide-react'
import { useResourceCRUD } from '@/hooks/use-resource-crud'
import { DeleteConfirmDialog } from '@/components/resource/delete-confirm-dialog'
import type { EmbeddedProps } from '@/types/resources'

interface MCPServer {
  id: number
  name: string
  description: string | null
  transport_type: string
  connection_config: Record<string, unknown>
  is_active: boolean
  last_discovered_at: string | null
  created_time: string
}

interface MCPTool {
  id: number
  mcp_server_id: number
  name: string
  description: string | null
  input_schema: Record<string, unknown> | null
}

const transportTypes = [
  { value: 'sse', label: 'SSE' },
  { value: 'streamable_http', label: 'Streamable HTTP' },
  { value: 'stdio', label: 'Stdio' },
]

export function MCPServersPage({ embedded, addDialogOpen, onAddDialogOpenChange }: EmbeddedProps = {}) {
  const { t } = useI18n()
  const [internalOpen, setInternalOpen] = useState(false)
  const open = addDialogOpen ?? internalOpen
  const setOpen = onAddDialogOpenChange ?? setInternalOpen
  const [transportType, setTransportType] = useState<string>('sse')
  const [deleteTarget, setDeleteTarget] = useState<MCPServer | null>(null)
  const [editTarget, setEditTarget] = useState<MCPServer | null>(null)
  const [editName, setEditName] = useState('')
  const [editDescription, setEditDescription] = useState('')

  const {
    items: servers, isLoading, isError,
    createMutation, updateMutation, deleteMutation, cloneMutation,
  } = useResourceCRUD<MCPServer>({
    endpoint: '/mcp-servers',
    queryKey: ['mcp-servers'],
    toastKeys: { created: 'mcp.created', updated: 'mcp.updated', deleted: 'mcp.deleted', cloned: 'common.cloneSuccess' },
  })

  function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    let connection_config: Record<string, unknown>
    if (transportType === 'stdio') {
      const argsStr = (fd.get('args') as string) || ''
      connection_config = {
        command: (fd.get('command') as string) || '',
        args: argsStr.split(',').map((s) => s.trim()).filter(Boolean),
      }
    } else {
      connection_config = { url: (fd.get('url') as string) || '' }
    }
    createMutation.mutate({
      name: fd.get('name') as string,
      description: (fd.get('description') as string) || undefined,
      transport_type: transportType,
      connection_config,
    }, { onSuccess: () => { setOpen(false); setTransportType('sse') } })
  }

  return (
    <div className={cn("flex flex-col flex-1", !embedded && "overflow-hidden")}>
      <div className={cn("overflow-auto flex-1", embedded ? "p-4" : "p-6")}>
      {!embedded && (
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">{t('mcp.title')}</h1>
          <Button onClick={() => setOpen(true)}>{t('mcp.createServer')}</Button>
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent className="max-w-lg max-h-[85vh] flex flex-col">
            <DialogHeader>
              <DialogTitle>{t('mcp.createServer')}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4 flex-1 overflow-y-auto pr-1">
              <div className="space-y-2">
                <Label htmlFor="name">{t('mcp.serverName')}</Label>
                <Input id="name" name="name" required placeholder={t('mcp.namePlaceholder')} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">{t('mcp.description')}</Label>
                <Input id="description" name="description" placeholder={t('mcp.descriptionPlaceholder')} />
              </div>
              <div className="space-y-2">
                <Label>{t('mcp.transportType')}</Label>
                <Select value={transportType} onValueChange={setTransportType}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {transportTypes.map((tt) => (
                      <SelectItem key={tt.value} value={tt.value}>{tt.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {(transportType === 'sse' || transportType === 'streamable_http') && (
                <div className="space-y-2">
                  <Label htmlFor="url">{t('mcp.url')}</Label>
                  <Input id="url" name="url" placeholder={t('mcp.urlPlaceholder')} />
                </div>
              )}
              {transportType === 'stdio' && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="command">{t('mcp.command')}</Label>
                    <Input id="command" name="command" placeholder={t('mcp.commandPlaceholder')} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="args">{t('mcp.args')}</Label>
                    <Input id="args" name="args" placeholder={t('mcp.argsPlaceholder')} />
                  </div>
                </div>
              )}
              <Button type="submit" className="w-full" disabled={createMutation.isPending}>
                {createMutation.isPending ? t('common.loading') : t('common.create')}
              </Button>
            </form>
          </DialogContent>
        </Dialog>

      {isLoading ? (
        <div className="text-muted-foreground">{t('common.loading')}</div>
      ) : isError ? (
        <div className="text-center py-12 text-destructive">{t('error.loadFailed')}</div>
      ) : !servers.length ? (
        <div className="text-center py-12 text-muted-foreground">{t('mcp.emptyHint')}</div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {servers.map((server) => (
            <Card
              key={server.id}
              className="cursor-pointer hover:bg-accent/50 transition-colors"
              onClick={() => { setEditTarget(server); setEditName(server.name); setEditDescription(server.description || '') }}
            >
              <CardHeader className="pb-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap min-w-0">
                    <CardTitle className="text-base truncate">{server.name}</CardTitle>
                    <Badge variant="outline">{server.transport_type}</Badge>
                    <Badge variant={server.is_active ? 'default' : 'secondary'}>
                      {server.is_active ? t('mcp.active') : t('mcp.inactive')}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                    <Button variant="outline" size="sm" className="gap-1" onClick={() => cloneMutation.mutate(server.id)} disabled={cloneMutation.isPending}>
                      <Copy className="h-3.5 w-3.5" />
                      {t('common.clone')}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                {server.description && <p className="text-sm text-muted-foreground">{server.description}</p>}
                <div className="flex gap-4 text-xs text-muted-foreground mt-1">
                  {server.connection_config && 'url' in server.connection_config && (
                    <span className="truncate">{String(server.connection_config.url)}</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={!!editTarget} onOpenChange={(v) => { if (!v) setEditTarget(null) }}>
        <DialogContent className="max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>{t('mcp.editServer')}</DialogTitle>
          </DialogHeader>
          {editTarget && (
            <div className="space-y-4 flex-1 overflow-y-auto pr-1">
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  updateMutation.mutate({
                    id: editTarget.id,
                    body: { name: editName, description: editDescription || null },
                  }, { onSuccess: () => setEditTarget(null) })
                }}
                className="space-y-4"
              >
                <div className="space-y-2">
                  <Label>{t('mcp.serverName')}</Label>
                  <Input value={editName} onChange={(e) => setEditName(e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label>{t('mcp.description')}</Label>
                  <Input value={editDescription} onChange={(e) => setEditDescription(e.target.value)} placeholder={t('mcp.descriptionPlaceholder')} />
                </div>
                <div className="flex gap-4 text-sm text-muted-foreground">
                  <span>{t('mcp.transportType')}: {editTarget.transport_type}</span>
                  {editTarget.connection_config && 'url' in editTarget.connection_config && (
                    <span className="truncate">{String(editTarget.connection_config.url)}</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button type="submit" className="flex-1" disabled={updateMutation.isPending}>
                    {updateMutation.isPending ? t('common.saving') : t('common.save')}
                  </Button>
                  <Button type="button" variant="destructive" onClick={() => setDeleteTarget(editTarget)}>
                    {t('common.delete')}
                  </Button>
                </div>
              </form>
              <MCPToolsList serverId={editTarget.id} />
            </div>
          )}
        </DialogContent>
      </Dialog>

      <DeleteConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => { if (!o) setDeleteTarget(null) }}
        itemName={deleteTarget?.name ?? ''}
        descriptionKey="mcp.confirmDelete"
        onConfirm={() => {
          if (deleteTarget) {
            deleteMutation.mutate(deleteTarget.id)
            setEditTarget(null)
          }
          setDeleteTarget(null)
        }}
      />

      </div>
    </div>
  )
}

function MCPToolsList({ serverId }: { serverId: number }) {
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ['mcp-server', serverId],
    queryFn: () => api.get<MCPServer & { tools?: MCPTool[] }>(`/mcp-servers/${serverId}`),
  })

  const discoverMutation = useMutation({
    mutationFn: () => api.post<MCPTool[]>(`/mcp-servers/${serverId}/discover`),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['mcp-server', serverId] })
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] })
      toast.success(t('mcp.discovered', { count: data?.length ?? 0 }))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const tools = detail?.tools ?? []

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label>{t('mcp.tools')} ({tools.length})</Label>
        <Button
          size="sm"
          variant="outline"
          onClick={() => discoverMutation.mutate()}
          disabled={discoverMutation.isPending}
        >
          {discoverMutation.isPending ? t('mcp.discovering') : t('mcp.discover')}
        </Button>
      </div>
      {detailLoading ? (
        <div className="text-sm text-muted-foreground py-4">{t('common.loading')}</div>
      ) : !tools.length ? (
        <div className="text-sm text-muted-foreground py-4">{t('mcp.noTools')}</div>
      ) : (
        <div className="space-y-2">
          {tools.map((tool) => (
            <div key={tool.id} className="flex flex-col gap-1 p-3 rounded border text-sm">
              <span className="font-medium">{tool.name}</span>
              {tool.description && (
                <span className="text-muted-foreground">{tool.description}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
