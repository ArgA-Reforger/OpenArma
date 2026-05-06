'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'
import { useState } from 'react'

interface PluginRaw {
  plugin: {
    name: string
    summary?: string
    version?: string
    description?: string
    author?: string
    enable: string
    tags?: string[]
  }
  [key: string]: unknown
}

export default function PluginsPage() {
  const api = useApi()
  const qc = useQueryClient()
  const [uninstallTarget, setUninstallTarget] = useState<string | null>(null)

  const { data: plugins, isLoading } = useQuery({
    queryKey: ['admin-plugins'],
    queryFn: () => api.get<PluginRaw[]>('/sys/plugins'),
  })

  const toggleMutation = useMutation({
    mutationFn: (name: string) => api.put(`/sys/plugins/${name}/status`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-plugins'] })
      toast.success('插件状态已更新')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const uninstallMutation = useMutation({
    mutationFn: (name: string) => api.delete(`/sys/plugins/${name}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-plugins'] })
      toast.success('插件已卸载')
      setUninstallTarget(null)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">插件管理</h1>

      {isLoading ? (
        <p className="text-muted-foreground">加载中...</p>
      ) : !plugins?.length ? (
        <p className="text-muted-foreground">暂无已安装插件</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {plugins.map((raw) => {
            const p = raw.plugin
            const enabled = p.enable === '1'
            return (
              <Card key={p.name}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{p.name}</CardTitle>
                    <Badge variant={enabled ? 'default' : 'secondary'}>
                      {enabled ? '启用' : '禁用'}
                    </Badge>
                  </div>
                  {p.summary && <p className="text-sm text-muted-foreground">{p.summary}</p>}
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    {p.author && <div><span className="text-muted-foreground">作者:</span> {p.author}</div>}
                    {p.version && <div><span className="text-muted-foreground">版本:</span> {p.version}</div>}
                    {p.tags?.length ? (
                      <div className="flex gap-1 flex-wrap">
                        {p.tags.map((tag) => (
                          <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                        ))}
                      </div>
                    ) : null}
                    {p.description && <p className="text-muted-foreground text-xs">{p.description}</p>}
                  </div>
                  <div className="flex gap-2 mt-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleMutation.mutate(p.name)}
                    >
                      {enabled ? '禁用' : '启用'}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive"
                      onClick={() => setUninstallTarget(p.name)}
                    >
                      卸载
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <AlertDialog open={!!uninstallTarget} onOpenChange={(open) => !open && setUninstallTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认卸载</AlertDialogTitle>
            <AlertDialogDescription>
              确定要卸载插件 <strong>{uninstallTarget}</strong> 吗？此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => uninstallTarget && uninstallMutation.mutate(uninstallTarget)}>卸载</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
