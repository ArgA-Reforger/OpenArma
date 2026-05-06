'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Cpu } from 'lucide-react'
import { VisibilityBadge, OfficialToggle } from './shared'
import type { ModelEntry } from '@/types/resources'

interface ShowcaseLLM {
  id: number | string
  name: string
  provider_type: string
  api_base: string | null
  models: ModelEntry[] | null
  is_active: boolean
  visibility: string
  user_id: number
}

export function LLMShowcase({ keyword, visibilityFilter }: { keyword: string; visibilityFilter?: string }) {
  const api = useApi()
  const { t } = useI18n()

  const { data, isLoading } = useQuery({
    queryKey: ['showcase-llm', keyword],
    queryFn: () => api.get<ShowcaseLLM[]>(`/showcase/llm-providers${keyword ? `?keyword=${keyword}` : ''}`),
  })

  const raw = Array.isArray(data) ? data : []
  const items = visibilityFilter ? raw.filter((i) => i.visibility === visibilityFilter) : raw

  if (isLoading) return <div className="text-muted-foreground">{t('common.loading')}</div>
  if (!items.length) return <div className="text-center py-12 text-muted-foreground">{t('showcase.empty')}</div>

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {items.map((provider) => (
        <Card key={String(provider.id)} className="hover:shadow-md transition-shadow">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <Cpu className="h-5 w-5 text-muted-foreground shrink-0" />
                <CardTitle className="text-base truncate">{provider.name}</CardTitle>
              </div>
              <div className="flex items-center gap-1">
                <Badge variant="outline">{provider.provider_type}</Badge>
                <VisibilityBadge visibility={provider.visibility} />
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {provider.models && provider.models.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {provider.models.slice(0, 5).map((model) => (
                  <Badge key={model.name} variant="secondary" className="text-xs">{model.name}</Badge>
                ))}
                {provider.models.length > 5 && (
                  <Badge variant="secondary" className="text-xs">+{provider.models.length - 5}</Badge>
                )}
              </div>
            )}
            <div className="flex justify-end">
              <OfficialToggle resourceType="llm-providers" id={provider.id} visibility={provider.visibility} queryKey={['showcase-llm', keyword]} />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
