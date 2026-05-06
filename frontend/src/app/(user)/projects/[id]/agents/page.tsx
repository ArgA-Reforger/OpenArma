'use client'

import { use, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Checkbox } from '@/components/ui/checkbox'
import { toast } from 'sonner'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { ExternalLink } from 'lucide-react'

interface Agent {
  id: number
  name: string
  description: string | null
  model_name: string | null
}

interface PageData<T> {
  items: T[]
  total: number
}

export default function ProjectAgentsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: pid } = use(params)
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()
  const [bindOpen, setBindOpen] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [unbindTarget, setUnbindTarget] = useState<Agent | null>(null)

  const { data: boundAgents = [], isLoading, isError } = useQuery({
    queryKey: ['project-agents', pid],
    queryFn: () => api.get<Agent[]>(`/projects/${pid}/agents`),
  })

  const { data: allAgents } = useQuery({
    queryKey: ['agents'],
    queryFn: () => api.get<PageData<Agent>>('/agents'),
  })

  const boundList = Array.isArray(boundAgents) ? boundAgents : []
  const boundIds = new Set(boundList.map((a) => a.id))
  const allItems = allAgents?.items ?? []
  const unboundAgents = allItems.filter((a) => !boundIds.has(a.id))

  const bindMutation = useMutation({
    mutationFn: (agentId: number) => api.post(`/projects/${pid}/agents?agent_id=${agentId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-agents', pid] })
      toast.success(t('agent.bound'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const unbindMutation = useMutation({
    mutationFn: (agentId: number) => api.delete(`/projects/${pid}/agents/${agentId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-agents', pid] })
      setUnbindTarget(null)
      toast.success(t('agent.unbound'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  function handleBind() {
    selectedIds.forEach((id) => bindMutation.mutate(id))
    setSelectedIds(new Set())
    setBindOpen(false)
  }

  function toggleSelect(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="p-6 overflow-auto flex-1">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{t('agent.boundAgents')}</h1>
        <div className="flex gap-2">
          <Link href="/resources">
            <Button size="sm" variant="outline">
              <ExternalLink className="h-4 w-4 mr-1" />
              {t('agent.title')}
            </Button>
          </Link>
          <Dialog open={bindOpen} onOpenChange={setBindOpen}>
            <DialogTrigger asChild>
              <Button size="sm">{t('agent.bindToProject')}</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t('agent.bindToProject')}</DialogTitle>
              </DialogHeader>
              <div className="space-y-2 max-h-60 overflow-auto">
                {!unboundAgents.length ? (
                  <p className="text-sm text-muted-foreground">{t('agent.emptyHint')}</p>
                ) : (
                  unboundAgents.map((agent) => (
                    <div
                      key={agent.id}
                      className="flex items-center gap-2 p-2 rounded border cursor-pointer hover:bg-accent"
                      onClick={() => toggleSelect(agent.id)}
                    >
                      <Checkbox checked={selectedIds.has(agent.id)} onCheckedChange={() => toggleSelect(agent.id)} />
                      <span className="font-medium">{agent.name}</span>
                      {agent.model_name && <span className="text-xs text-muted-foreground">{agent.model_name}</span>}
                    </div>
                  ))
                )}
              </div>
              <Button
                onClick={handleBind}
                disabled={selectedIds.size === 0 || bindMutation.isPending}
                className="w-full mt-4"
              >
                {t('common.add')}
              </Button>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">{t('common.loading')}</div>
      ) : isError ? (
        <div className="text-center py-12 text-destructive">{t('error.loadFailed')}</div>
      ) : !boundList.length ? (
        <div className="text-center py-12 text-muted-foreground">{t('agent.emptyHint')}</div>
      ) : (
        <div className="space-y-3">
          {boundList.map((agent) => (
            <Card key={agent.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-base">{agent.name}</CardTitle>
                    {agent.model_name && <span className="text-sm text-muted-foreground">{agent.model_name}</span>}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    onClick={() => setUnbindTarget(agent)}
                  >
                    {t('agent.unbound')}
                  </Button>
                </div>
                {agent.description && <p className="text-sm text-muted-foreground mt-1">{agent.description}</p>}
              </CardHeader>
            </Card>
          ))}
        </div>
      )}

      <AlertDialog open={!!unbindTarget} onOpenChange={(o) => !o && setUnbindTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('error.confirmDelete')}</AlertDialogTitle>
            <AlertDialogDescription>{t('agent.confirmUnbind', { name: unbindTarget?.name ?? '' })}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={() => unbindTarget && unbindMutation.mutate(unbindTarget.id)}>
              {t('agent.unbound')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
