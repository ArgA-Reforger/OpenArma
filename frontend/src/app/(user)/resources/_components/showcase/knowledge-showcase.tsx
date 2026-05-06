'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { BindToProjectDialog } from '@/components/bind-to-project-dialog'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { BookOpen, Copy } from 'lucide-react'
import { toast } from 'sonner'
import { VisibilityBadge, BindButton, OfficialToggle } from './shared'

interface ShowcaseKB {
  id: number | string
  name: string
  description: string | null
  embedding_model: string
  document_count: number
  status: string
  visibility: string
  user_id: number
}

export function KnowledgeShowcase({ keyword, visibilityFilter }: { keyword: string; visibilityFilter?: string }) {
  const api = useApi()
  const queryClient = useQueryClient()
  const router = useRouter()
  const { t } = useI18n()
  const [bindTarget, setBindTarget] = useState<ShowcaseKB | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['showcase-knowledge', keyword],
    queryFn: () => api.get<ShowcaseKB[]>(`/showcase/knowledge-bases${keyword ? `?keyword=${keyword}` : ''}`),
  })

  const cloneMutation = useMutation({
    mutationFn: (id: number | string) => api.post(`/knowledge-bases/${id}/clone`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] })
      toast.success(t('common.cloneSuccess'))
      router.push('/resources')
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const raw = Array.isArray(data) ? data : []
  const items = visibilityFilter ? raw.filter((i) => i.visibility === visibilityFilter) : raw

  if (isLoading) return <div className="text-muted-foreground">{t('common.loading')}</div>
  if (!items.length) return <div className="text-center py-12 text-muted-foreground">{t('showcase.empty')}</div>

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {items.map((kb) => (
          <Card key={String(kb.id)} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <BookOpen className="h-5 w-5 text-muted-foreground shrink-0" />
                  <CardTitle className="text-base truncate">{kb.name}</CardTitle>
                </div>
                <VisibilityBadge visibility={kb.visibility} />
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {kb.description && <p className="text-sm text-muted-foreground line-clamp-2">{kb.description}</p>}
                <div className="flex items-center justify-between">
                <div className="flex gap-2 text-xs text-muted-foreground">
                  <span>{t('knowledge.documentCount')}: {kb.document_count}</span>
                  <span>{kb.embedding_model}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <OfficialToggle resourceType="knowledge-bases" id={kb.id} visibility={kb.visibility} queryKey={['showcase-knowledge', keyword]} />
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5"
                    onClick={(e) => { e.stopPropagation(); cloneMutation.mutate(kb.id) }}
                    disabled={cloneMutation.isPending}
                  >
                    <Copy className="h-3.5 w-3.5" />
                    {t('common.clone')}
                  </Button>
                  <BindButton onClick={() => setBindTarget(kb)} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      {bindTarget && (
        <BindToProjectDialog
          open={!!bindTarget}
          onOpenChange={(v) => { if (!v) setBindTarget(null) }}
          resourceId={bindTarget.id}
          resourceType="knowledge-base"
          resourceName={bindTarget.name}
        />
      )}
    </>
  )
}
