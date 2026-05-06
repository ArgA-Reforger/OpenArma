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
import { Checkbox } from '@/components/ui/checkbox'
import { toast } from 'sonner'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { ExternalLink } from 'lucide-react'

interface KnowledgeBase {
  id: number
  name: string
  description: string | null
  embedding_model: string
  chunk_size: number
  chunk_overlap: number
  document_count: number
  status: string
  created_time: string
}

interface PageData<T> {
  items: T[]
  total: number
}

export default function ProjectKnowledgePage({ params }: { params: Promise<{ id: string }> }) {
  const { id: pid } = use(params)
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()
  const [bindOpen, setBindOpen] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [unbindTarget, setUnbindTarget] = useState<KnowledgeBase | null>(null)

  const { data: boundData, isLoading, isError } = useQuery({
    queryKey: ['project-knowledge-bases', pid],
    queryFn: () => api.get<KnowledgeBase[]>(`/projects/${pid}/knowledge-bases`),
  })

  const { data: allKbs } = useQuery({
    queryKey: ['knowledge-bases'],
    queryFn: () => api.get<PageData<KnowledgeBase>>('/knowledge-bases'),
  })

  const boundKbs = Array.isArray(boundData) ? boundData : []
  const boundIds = new Set(boundKbs.map((kb) => kb.id))
  const allItems = allKbs?.items ?? []
  const unboundKbs = allItems.filter((kb) => !boundIds.has(kb.id))

  const bindMutation = useMutation({
    mutationFn: (kbId: number) => api.post(`/projects/${pid}/knowledge-bases?kb_id=${kbId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-knowledge-bases', pid] })
      toast.success(t('knowledge.bound'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const unbindMutation = useMutation({
    mutationFn: (kbId: number) => api.delete(`/projects/${pid}/knowledge-bases/${kbId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-knowledge-bases', pid] })
      setUnbindTarget(null)
      toast.success(t('knowledge.unbound'))
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
        <h1 className="text-2xl font-bold">{t('knowledge.boundKBs')}</h1>
        <div className="flex gap-2">
          <Link href="/resources">
            <Button size="sm" variant="outline">
              <ExternalLink className="h-4 w-4 mr-1" />
              {t('knowledge.title')}
            </Button>
          </Link>
          <Dialog open={bindOpen} onOpenChange={setBindOpen}>
            <DialogTrigger asChild>
              <Button size="sm">{t('knowledge.bindToProject')}</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t('knowledge.bindToProject')}</DialogTitle>
              </DialogHeader>
              <div className="space-y-2 max-h-60 overflow-auto">
                {!unboundKbs.length ? (
                  <p className="text-sm text-muted-foreground">{t('knowledge.emptyHint')}</p>
                ) : (
                  unboundKbs.map((kb) => (
                    <div
                      key={kb.id}
                      className="flex items-center gap-2 p-2 rounded border cursor-pointer hover:bg-accent"
                      onClick={() => toggleSelect(kb.id)}
                    >
                      <Checkbox checked={selectedIds.has(kb.id)} onCheckedChange={() => toggleSelect(kb.id)} />
                      <span className="font-medium">{kb.name}</span>
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
      ) : !boundKbs.length ? (
        <div className="text-center py-12 text-muted-foreground">{t('knowledge.emptyHint')}</div>
      ) : (
        <div className="space-y-3">
          {boundKbs.map((kb) => (
            <Card key={kb.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base">{kb.name}</CardTitle>
                    {kb.description && (
                      <p className="text-sm text-muted-foreground mt-1">{kb.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                      {t('knowledge.documentCount')}: {kb.document_count}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive"
                      onClick={() => setUnbindTarget(kb)}
                    >
                      {t('knowledge.unbound')}
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
              {t('knowledge.confirmUnbind', { name: unbindTarget?.name ?? '' })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={() => unbindTarget && unbindMutation.mutate(unbindTarget.id)}>
              {t('knowledge.unbound')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
