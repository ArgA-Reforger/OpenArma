'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { Wrench, ArrowRight } from 'lucide-react'
import Link from 'next/link'
import type { EmbeddedProps } from '@/types/resources'

interface BuiltinTool {
  id: number | string
  name: string
  display_name: string
  description: string
  handler_type: string
  category: string
  is_system: boolean
  is_active: boolean
}

const CATEGORY_COLORS: Record<string, string> = {
  general: '',
  arma: 'bg-amber-500/10 text-amber-600 border-amber-300',
  map: 'bg-emerald-500/10 text-emerald-600 border-emerald-300',
}

export function BuiltinToolsPage({ embedded }: EmbeddedProps = {}) {
  const api = useApi()
  const { t } = useI18n()

  const { data: tools, isLoading } = useQuery({
    queryKey: ['builtin-tools-active'],
    queryFn: () => api.get<BuiltinTool[]>('/builtin-tools/active'),
  })

  return (
    <div className="overflow-auto h-full">
      <div className={cn("space-y-6", embedded ? "p-4" : "max-w-4xl mx-auto p-6")}>
        {!embedded && (
          <div>
            <h1 className="text-2xl font-bold">{t('builtinTool.pageTitle')}</h1>
            <p className="text-muted-foreground mt-1">{t('builtinTool.pageDesc')}</p>
          </div>
        )}

        {isLoading ? (
          <div className="text-center py-12 text-muted-foreground animate-pulse">...</div>
        ) : !tools?.length ? (
          <div className="text-center py-16 text-muted-foreground">
            <Wrench className="h-12 w-12 mx-auto mb-3 opacity-40" />
            <p>{t('builtinTool.noActiveTools')}</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {tools.map((tool) => (
              <Card key={String(tool.id)}>
                <CardHeader className="pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <Wrench className="h-4 w-4 text-muted-foreground shrink-0" />
                      <CardTitle className="text-base truncate">{(() => { const k = `builtinTool.tool_${tool.name}`; const v = t(k); return v !== k ? v : tool.display_name })()}</CardTitle>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {tool.category !== 'general' && (
                        <Badge variant="outline" className={CATEGORY_COLORS[tool.category] || ''}>
                          {tool.category.toUpperCase()}
                        </Badge>
                      )}
                      {tool.is_system && (
                        <Badge variant="outline">{t('builtinTool.system')}</Badge>
                      )}
                      <Badge variant={tool.is_active ? 'default' : 'secondary'}>
                        {tool.is_active ? t('builtinTool.active') : t('builtinTool.inactive')}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0 space-y-2">
                  <p className="text-sm text-muted-foreground">{(() => { const k = `builtinTool.toolDesc_${tool.name}`; const v = t(k); return v !== k ? v : tool.description })()}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      {t('builtinTool.handlerLabel')}: {tool.handler_type}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {!embedded && (
          <div className="flex justify-center pt-4">
            <Button variant="outline" asChild>
              <Link href="/resources" className="flex items-center gap-2">
                {t('builtinTool.viewInAgent')}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
