'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import type { PageData } from '@/types/resources'

type ResourceType = 'agent' | 'knowledge-base' | 'mcp'

interface Project {
  id: number | string
  name: string
  status: string
}

export function BindToProjectDialog({
  open,
  onOpenChange,
  resourceId,
  resourceType,
  resourceName,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  resourceId: number | string
  resourceType: ResourceType
  resourceName: string
}) {
  const api = useApi()
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)

  const { data: projectsData, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.get<PageData<Project>>('/projects'),
    enabled: open,
  })

  const bindMutation = useMutation({
    mutationFn: async ({ projectId }: { projectId: string }) => {
      const rid = String(resourceId)
      switch (resourceType) {
        case 'agent':
          return api.post(`/projects/${projectId}/agents?agent_id=${rid}`)
        case 'knowledge-base':
          return api.post(`/projects/${projectId}/knowledge-bases?kb_id=${rid}`)
        case 'mcp':
          return api.post(`/projects/${projectId}/mcps`, { mcp_server_id: Number(rid) })
      }
    },
    onSuccess: () => {
      toast.success(t('showcase.bindSuccess'))
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      onOpenChange(false)
      setSelectedProjectId(null)
    },
    onError: (err: Error) => {
      toast.error(err.message || t('showcase.bindFailed'))
    },
  })

  const projects = projectsData?.items || []

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) setSelectedProjectId(null) }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t('showcase.selectProject')}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground mb-2">
          {t('showcase.selectProjectHint')}
        </p>
        <p className="text-sm font-medium mb-4 truncate" title={resourceName}>
          {resourceName}
        </p>
        {isLoading ? (
          <div className="text-center py-4 text-sm text-muted-foreground">{t('common.loading')}</div>
        ) : !projects.length ? (
          <div className="text-center py-4 text-sm text-muted-foreground">{t('showcase.noProjects')}</div>
        ) : (
          <div className="space-y-1 max-h-60 overflow-auto">
            {projects.map((p) => {
              const pid = String(p.id)
              return (
                <button
                  key={pid}
                  onClick={() => setSelectedProjectId(pid)}
                  className={cn(
                    'w-full text-left px-3 py-2 rounded-md text-sm transition-colors',
                    selectedProjectId === pid
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-accent',
                  )}
                >
                  {p.name}
                </button>
              )
            })}
          </div>
        )}
        <DialogFooter>
          <Button
            disabled={!selectedProjectId || bindMutation.isPending}
            onClick={() => { if (selectedProjectId) bindMutation.mutate({ projectId: selectedProjectId }) }}
          >
            {bindMutation.isPending ? t('common.loading') : t('showcase.bindToProject')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
