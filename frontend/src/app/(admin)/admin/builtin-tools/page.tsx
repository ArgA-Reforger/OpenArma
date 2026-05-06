'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'

interface BuiltinTool {
  id: number
  name: string
  display_name: string
  description: string
  input_schema: Record<string, unknown>
  handler_type: string
  handler_config: Record<string, unknown> | null
  is_system: boolean
  is_active: boolean
  created_time: string
}

interface PageData<T> {
  items: T[]
  total: number
}

export default function BuiltinToolsPage() {
  const api = useApi()
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<BuiltinTool | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<BuiltinTool | null>(null)
  const { t } = useI18n()

  const { data, isLoading } = useQuery({
    queryKey: ['admin-builtin-tools'],
    queryFn: () => api.get<PageData<BuiltinTool>>('/builtin-tools'),
  })

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/builtin-tools', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-builtin-tools'] })
      setCreateOpen(false)
      toast.success(t('builtinTool.created'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Record<string, unknown> }) =>
      api.put(`/builtin-tools/${id}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-builtin-tools'] })
      setEditTarget(null)
      toast.success(t('builtinTool.updated'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/builtin-tools/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-builtin-tools'] })
      setDeleteTarget(null)
      toast.success(t('builtinTool.deleted'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    let schema = {}
    try { schema = JSON.parse(fd.get('input_schema') as string || '{}') } catch { /* */ }
    createMutation.mutate({
      name: fd.get('name') as string,
      display_name: fd.get('display_name') as string,
      description: fd.get('description') as string,
      input_schema: schema,
      handler_type: (fd.get('handler_type') as string) || 'python_builtin',
      is_system: false,
      is_active: true,
    })
  }

  function handleUpdate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!editTarget) return
    const fd = new FormData(e.currentTarget)
    const body: Record<string, unknown> = {
      display_name: fd.get('display_name') as string,
      description: fd.get('description') as string,
      is_active: (fd.get('is_active') as string) === 'on',
    }
    updateMutation.mutate({ id: editTarget.id, body })
  }

  function toggleActive(tool: BuiltinTool) {
    updateMutation.mutate({
      id: tool.id,
      body: { is_active: !tool.is_active },
    })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('builtinTool.title')}</h1>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button>{t('builtinTool.create')}</Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>{t('builtinTool.create')}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">{t('builtinTool.toolName')}</Label>
                <Input id="name" name="name" required placeholder="web_search" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="display_name">{t('builtinTool.displayName')}</Label>
                <Input id="display_name" name="display_name" required placeholder={t('builtinTool.displayNamePlaceholder')} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">{t('builtinTool.description')}</Label>
                <Textarea id="description" name="description" required rows={3} placeholder={t('builtinTool.descriptionPlaceholder')} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="input_schema">{t('builtinTool.inputSchema')}</Label>
                <Textarea id="input_schema" name="input_schema" rows={4} placeholder='{"type": "object", "properties": {...}}' />
              </div>
              <div className="space-y-2">
                <Label htmlFor="handler_type">{t('builtinTool.handlerType')}</Label>
                <Input id="handler_type" name="handler_type" defaultValue="python_builtin" />
              </div>
              <Button type="submit" className="w-full" disabled={createMutation.isPending}>
                {createMutation.isPending ? t('common.loading') : t('common.create')}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">{t('common.loading')}</div>
      ) : !data?.items?.length ? (
        <div className="text-center py-12 text-muted-foreground">{t('builtinTool.empty')}</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {data.items.map((tool) => (
            <Card key={tool.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-base">{tool.display_name}</CardTitle>
                    <Badge variant={tool.is_active ? 'default' : 'secondary'}>
                      {tool.is_active ? t('common.enabled') : t('common.disabled')}
                    </Badge>
                    {tool.is_system && <Badge variant="outline">{t('builtinTool.system')}</Badge>}
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" onClick={() => toggleActive(tool)}>
                      {tool.is_active ? t('common.disabled') : t('common.enabled')}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setEditTarget(tool)}>
                      {t('common.edit')}
                    </Button>
                    {!tool.is_system && (
                      <Button variant="ghost" size="sm" className="text-destructive" onClick={() => setDeleteTarget(tool)}>
                        {t('common.delete')}
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0 space-y-1">
                <p className="text-sm text-muted-foreground">{tool.description}</p>
                <div className="flex gap-4 text-xs text-muted-foreground">
                  <span>{t('builtinTool.toolName')}: {tool.name}</span>
                  <span>{t('builtinTool.handlerType')}: {tool.handler_type}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={!!editTarget} onOpenChange={(o) => { if (!o) setEditTarget(null) }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{t('builtinTool.edit')}</DialogTitle>
          </DialogHeader>
          {editTarget && (
            <form onSubmit={handleUpdate} className="space-y-4">
              <div className="space-y-2">
                <Label>{t('builtinTool.toolName')}</Label>
                <Input value={editTarget.name} disabled />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-display_name">{t('builtinTool.displayName')}</Label>
                <Input id="edit-display_name" name="display_name" defaultValue={editTarget.display_name} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-description">{t('builtinTool.description')}</Label>
                <Textarea id="edit-description" name="description" rows={3} defaultValue={editTarget.description} />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="edit-is_active" name="is_active" defaultChecked={editTarget.is_active} className="rounded border-input" />
                <Label htmlFor="edit-is_active" className="cursor-pointer">{t('common.enabled')}</Label>
              </div>
              <Button type="submit" className="w-full" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? t('common.saving') : t('common.save')}
              </Button>
            </form>
          )}
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('error.confirmDelete')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('builtinTool.confirmDelete', { name: deleteTarget?.display_name ?? '' })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={() => { if (deleteTarget) deleteMutation.mutate(deleteTarget.id) }}>
              {t('common.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
