'use client'

import { use, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { ExternalLink } from 'lucide-react'

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

interface PageData<T> {
  items: T[]
  total: number
}

export default function ProjectMCPPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: pid } = use(params)
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()
  const [bindOpen, setBindOpen] = useState(false)
  const [unbindTarget, setUnbindTarget] = useState<MCPServer | null>(null)

  const { data: boundIds = [], isLoading, isError } = useQuery({
    queryKey: ['project-mcps', pid],
    queryFn: () => api.get<number[]>(`/projects/${pid}/mcps`),
  })

  const { data: allServers } = useQuery({
    queryKey: ['mcp-servers'],
    queryFn: () => api.get<PageData<MCPServer>>('/mcp-servers'),
  })

  const boundSet = new Set(boundIds)
  const servers = allServers?.items ?? []
  const boundServers = servers.filter((s) => boundSet.has(s.id))
  const unboundServers = servers.filter((s) => !boundSet.has(s.id))

  const bindMutation = useMutation({
    mutationFn: (mcpServerId: number) => api.post(`/projects/${pid}/mcps`, { mcp_server_id: mcpServerId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-mcps', pid] })
      setBindOpen(false)
      toast.success(t('mcp.bound'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const unbindMutation = useMutation({
    mutationFn: (mcpServerId: number) => api.delete(`/projects/${pid}/mcps/${mcpServerId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-mcps', pid] })
      setUnbindTarget(null)
      toast.success(t('mcp.unbound'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  return (
    <div className="p-6 overflow-auto flex-1">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{t('mcp.title')}</h1>
        <div className="flex gap-2">
          <Link href="/resources">
            <Button size="sm" variant="outline">
              <ExternalLink className="h-4 w-4 mr-1" />
              {t('mcp.title')}
            </Button>
          </Link>
          <Dialog open={bindOpen} onOpenChange={setBindOpen}>
            <DialogTrigger asChild>
              <Button size="sm">{t('mcp.bindToProject')}</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t('mcp.bindToProject')}</DialogTitle>
              </DialogHeader>
              <div className="space-y-2 max-h-60 overflow-auto">
                {!unboundServers.length ? (
                  <p className="text-sm text-muted-foreground">{t('mcp.emptyHint')}</p>
                ) : (
                  unboundServers.map((server) => (
                    <div key={server.id} className="flex items-center justify-between p-2 rounded border">
                      <span className="font-medium">{server.name}</span>
                      <Button
                        size="sm"
                        onClick={() => bindMutation.mutate(server.id)}
                        disabled={bindMutation.isPending}
                      >
                        {t('common.add')}
                      </Button>
                    </div>
                  ))
                )}
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">{t('common.loading')}</div>
      ) : isError ? (
        <div className="text-center py-12 text-destructive">{t('error.loadFailed')}</div>
      ) : !boundServers.length ? (
        <div className="text-center py-12 text-muted-foreground">{t('mcp.emptyHint')}</div>
      ) : (
        <div className="space-y-3">
          {boundServers.map((server) => (
            <Card key={server.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base">{server.name}</CardTitle>
                    {server.description && (
                      <p className="text-sm text-muted-foreground mt-1">{server.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{server.transport_type}</Badge>
                    <Badge variant={server.is_active ? 'default' : 'secondary'}>
                      {server.is_active ? t('mcp.active') : t('mcp.inactive')}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive"
                      onClick={() => setUnbindTarget(server)}
                    >
                      {t('mcp.unbound')}
                    </Button>
                  </div>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}

      <AlertDialog open={!!unbindTarget} onOpenChange={(o) => !o && setUnbindTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('error.confirmDelete')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('mcp.confirmUnbind', { name: unbindTarget?.name ?? '' })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={() => unbindTarget && unbindMutation.mutate(unbindTarget.id)}>
              {t('mcp.unbound')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
