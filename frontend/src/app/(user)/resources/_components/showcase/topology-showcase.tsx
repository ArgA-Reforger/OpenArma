'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Workflow, Copy } from 'lucide-react'
import { toast } from 'sonner'
import { VisibilityBadge, OfficialToggle } from './shared'

interface ShowcaseTopology {
  id: number | string
  name: string
  description: string | null
  visibility: string
  user_id: number
}

export function TopologyShowcase({ keyword, visibilityFilter }: { keyword: string; visibilityFilter?: string }) {
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()

  const params = new URLSearchParams()
  if (keyword) params.set('keyword', keyword)
  if (visibilityFilter) params.set('visibility', visibilityFilter)

  const { data, isLoading } = useQuery({
    queryKey: ['showcase-topologies', keyword, visibilityFilter ?? ''],
    queryFn: () => api.get<ShowcaseTopology[]>(`/showcase/topologies?${params.toString()}`),
  })

  const cloneMutation = useMutation({
    mutationFn: (id: number | string) => api.post(`/topologies/${id}/clone`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topologies'] })
      toast.success(t('topology.cloned'))
    },
    onError: () => toast.error(t('common.error')),
  })

  if (isLoading) return <p className="text-sm text-muted-foreground">{t('common.loading')}</p>
  if (!data?.length) return <p className="text-sm text-muted-foreground">{t('common.noData')}</p>

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {data.map((topo) => (
        <Card key={topo.id}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <Workflow className="h-5 w-5 text-muted-foreground shrink-0" />
                <CardTitle className="text-base truncate">{topo.name}</CardTitle>
              </div>
              <VisibilityBadge visibility={topo.visibility} />
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {topo.description && (
              <p className="text-xs text-muted-foreground line-clamp-2">{topo.description}</p>
            )}
            <div className="flex items-center gap-1.5">
              <OfficialToggle resourceType="topologies" id={topo.id} visibility={topo.visibility} queryKey={['showcase-topologies', keyword, visibilityFilter ?? '']} />
              <Button
                size="sm"
                variant="ghost"
                className="h-7 text-xs"
                onClick={() => cloneMutation.mutate(topo.id)}
              >
                <Copy className="h-3 w-3 mr-1" />
                {t('common.clone')}
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
