'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { BindToProjectDialog } from '@/components/bind-to-project-dialog'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Bot, Copy } from 'lucide-react'
import { toast } from 'sonner'
import { VisibilityBadge, BindButton, OfficialToggle } from './shared'

interface ShowcaseAgent {
  id: number | string
  name: string
  description: string | null
  model_name: string | null
  visibility: string
  user_id: number
}

export function AgentsShowcase({ keyword, visibilityFilter }: { keyword: string; visibilityFilter?: string }) {
  const api = useApi()
  const queryClient = useQueryClient()
  const router = useRouter()
  const { t } = useI18n()
  const [bindTarget, setBindTarget] = useState<ShowcaseAgent | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['showcase-agents', keyword],
    queryFn: () => api.get<ShowcaseAgent[]>(`/showcase/agents${keyword ? `?keyword=${keyword}` : ''}`),
  })

  const cloneMutation = useMutation({
    mutationFn: (id: number | string) => api.post(`/agents/${id}/clone`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
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
        {items.map((agent) => (
          <Card key={String(agent.id)} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <Bot className="h-5 w-5 text-muted-foreground shrink-0" />
                  <CardTitle className="text-base truncate">{agent.name}</CardTitle>
                </div>
                <VisibilityBadge visibility={agent.visibility} />
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {agent.description && <p className="text-sm text-muted-foreground line-clamp-2">{agent.description}</p>}
                <div className="flex items-center justify-between">
                <div className="flex gap-2 text-xs text-muted-foreground">
                  {agent.model_name && <span>{t('agent.model')}: {agent.model_name}</span>}
                </div>
                <div className="flex items-center gap-1.5">
                  <OfficialToggle resourceType="agents" id={agent.id} visibility={agent.visibility} queryKey={['showcase-agents', keyword]} />
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5"
                    onClick={(e) => { e.stopPropagation(); cloneMutation.mutate(agent.id) }}
                    disabled={cloneMutation.isPending}
                  >
                    <Copy className="h-3.5 w-3.5" />
                    {t('common.clone')}
                  </Button>
                  <BindButton onClick={() => setBindTarget(agent)} />
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
          resourceType="agent"
          resourceName={bindTarget.name}
        />
      )}
    </>
  )
}
