'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { BindToProjectDialog } from '@/components/bind-to-project-dialog'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Wrench, Copy } from 'lucide-react'
import { toast } from 'sonner'
import { VisibilityBadge, BindButton, OfficialToggle } from './shared'

interface ShowcaseMCP {
  id: number | string
  name: string
  description: string | null
  transport_type: string
  is_active: boolean
  visibility: string
  user_id: number
}

export function MCPShowcase({ keyword, visibilityFilter }: { keyword: string; visibilityFilter?: string }) {
  const api = useApi()
  const queryClient = useQueryClient()
  const router = useRouter()
  const { t } = useI18n()
  const [bindTarget, setBindTarget] = useState<ShowcaseMCP | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['showcase-mcps', keyword],
    queryFn: () => api.get<ShowcaseMCP[]>(`/showcase/mcp-servers${keyword ? `?keyword=${keyword}` : ''}`),
  })

  const cloneMutation = useMutation({
    mutationFn: (id: number | string) => api.post(`/mcp-servers/${id}/clone`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] })
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
        {items.map((server) => (
          <Card key={String(server.id)} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <Wrench className="h-5 w-5 text-muted-foreground shrink-0" />
                  <CardTitle className="text-base truncate">{server.name}</CardTitle>
                </div>
                <div className="flex items-center gap-1">
                  <Badge variant="outline">{server.transport_type}</Badge>
                  <VisibilityBadge visibility={server.visibility} />
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {server.description && <p className="text-sm text-muted-foreground line-clamp-2">{server.description}</p>}
              <div className="flex justify-end gap-1.5">
                <OfficialToggle resourceType="mcp-servers" id={server.id} visibility={server.visibility} queryKey={['showcase-mcps', keyword]} />
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={(e) => { e.stopPropagation(); cloneMutation.mutate(server.id) }}
                  disabled={cloneMutation.isPending}
                >
                  <Copy className="h-3.5 w-3.5" />
                  {t('common.clone')}
                </Button>
                <BindButton onClick={() => setBindTarget(server)} />
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
          resourceType="mcp"
          resourceName={bindTarget.name}
        />
      )}
    </>
  )
}
