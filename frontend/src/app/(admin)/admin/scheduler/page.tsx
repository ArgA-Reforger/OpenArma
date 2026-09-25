'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'

interface Task {
  id: number
  name: string
  group: string
  module: string
  func: string
  args: unknown[] | null
  kwargs: Record<string, unknown> | null
  trigger: string
  trigger_args: string
  executor: string
  coalesce: boolean
  misfire_grace_time: number | null
  max_instances: number
  next_run_time: string | null
  enabled: boolean
  total_run_count: number
  remark: string | null
  created_time: string
}

interface PageData<T> {
  items: T[]
  total: number
  page: number
  size: number
  total_pages: number
}

export default function SchedulerPage() {
  const api = useApi()
  const qc = useQueryClient()
  const { t, locale } = useI18n()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editTask, setEditTask] = useState<Task | null>(null)
  const [deleteTask, setDeleteTask] = useState<Task | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-scheduler', page, search],
    queryFn: () =>
      api.get<PageData<Task>>(`/schedulers?page=${page}&size=20${search ? `&name=${search}` : ''}`),
  })

  const { data: registeredTasks } = useQuery({
    queryKey: ['admin-registered-tasks'],
    queryFn: () => api.get<string[]>('/tasks/registered'),
  })

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/schedulers', body),
    onSuccess: () => { toast.success(t('scheduler.taskCreated')); qc.invalidateQueries({ queryKey: ['admin-scheduler'] }); setFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ pk, body }: { pk: number; body: Record<string, unknown> }) => api.put(`/schedulers/${pk}`, body),
    onSuccess: () => { toast.success(t('scheduler.taskUpdated')); qc.invalidateQueries({ queryKey: ['admin-scheduler'] }); setEditTask(null); setFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const toggleMutation = useMutation({
    mutationFn: (pk: number) => api.put(`/schedulers/${pk}/status`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-scheduler'] }),
    onError: (e: Error) => toast.error(e.message),
  })

  const executeMutation = useMutation({
    mutationFn: (pk: number) => api.post(`/schedulers/${pk}/execute`),
    onSuccess: () => toast.success(t('scheduler.taskExecuted')),
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (pk: number) => api.delete(`/schedulers/${pk}`),
    onSuccess: () => { toast.success(t('scheduler.taskDeleted')); qc.invalidateQueries({ queryKey: ['admin-scheduler'] }); setDeleteTask(null) },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('scheduler.title')}</h1>
        <Button onClick={() => { setEditTask(null); setFormOpen(true) }}>{t('scheduler.createTask')}</Button>
      </div>

      <Input placeholder={t('scheduler.searchTask')} value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} className="max-w-xs" />

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('scheduler.taskName')}</TableHead>
              <TableHead>{t('scheduler.trigger')}</TableHead>
              <TableHead>{t('scheduler.expression')}</TableHead>
              <TableHead>{t('common.status')}</TableHead>
              <TableHead>{t('scheduler.runCount')}</TableHead>
              <TableHead>{t('scheduler.nextRun')}</TableHead>
              <TableHead className="text-right">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={7} className="text-center py-8 text-muted-foreground">{t('common.loading')}</TableCell></TableRow>
            ) : !data?.items?.length ? (
              <TableRow><TableCell colSpan={7} className="text-center py-8 text-muted-foreground">{t('common.noData')}</TableCell></TableRow>
            ) : (
              data.items.map((task) => (
                <TableRow key={task.id}>
                  <TableCell>
                    <div>
                      <span className="font-medium">{task.name}</span>
                      <p className="text-xs text-muted-foreground">{task.module}.{task.func}</p>
                    </div>
                  </TableCell>
                  <TableCell><Badge variant="outline">{task.trigger}</Badge></TableCell>
                  <TableCell><code className="text-xs bg-muted px-1 rounded">{task.trigger_args}</code></TableCell>
                  <TableCell>
                    <Badge
                      variant={task.enabled ? 'default' : 'secondary'}
                      className="cursor-pointer"
                      onClick={() => toggleMutation.mutate(task.id)}
                    >
                      {task.enabled ? t('scheduler.running') : t('scheduler.paused')}
                    </Badge>
                  </TableCell>
                  <TableCell>{task.total_run_count}</TableCell>
                  <TableCell className="text-xs">
                    {task.next_run_time ? new Date(task.next_run_time).toLocaleString(locale) : '-'}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="sm" onClick={() => executeMutation.mutate(task.id)}>{t('scheduler.execute')}</Button>
                      <Button variant="ghost" size="sm" onClick={() => { setEditTask(task); setFormOpen(true) }}>{t('common.edit')}</Button>
                      <Button variant="ghost" size="sm" className="text-destructive" onClick={() => setDeleteTask(task)}>{t('common.delete')}</Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">{t('common.total', { total: data.total })}</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>{t('common.prevPage')}</Button>
            <Button variant="outline" size="sm" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)}>{t('common.nextPage')}</Button>
          </div>
        </div>
      )}

      <TaskFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        task={editTask}
        registeredTasks={registeredTasks ?? []}
        onSubmit={(body) => editTask ? updateMutation.mutate({ pk: editTask.id, body }) : createMutation.mutate(body)}
        loading={createMutation.isPending || updateMutation.isPending}
      />

      <AlertDialog open={!!deleteTask} onOpenChange={(open) => !open && setDeleteTask(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('common.confirmDelete')}</AlertDialogTitle>
            <AlertDialogDescription>{t('scheduler.confirmDelete', { name: deleteTask?.name ?? '' })}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteTask && deleteMutation.mutate(deleteTask.id)}>{t('common.delete')}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function TaskFormDialog({
  open, onOpenChange, task, registeredTasks, onSubmit, loading,
}: {
  open: boolean; onOpenChange: (open: boolean) => void; task: Task | null
  registeredTasks: string[]; onSubmit: (body: Record<string, unknown>) => void; loading: boolean
}) {
  const { t } = useI18n()

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const taskPath = fd.get('task') as string
    const parts = taskPath.split('.')
    const func = parts.pop()!
    const module = parts.join('.')
    onSubmit({
      name: fd.get('name'),
      group: fd.get('group') || 'default',
      module,
      func,
      trigger: fd.get('trigger'),
      trigger_args: fd.get('trigger_args'),
      executor: fd.get('executor') || 'default',
      max_instances: Number(fd.get('max_instances') || 1),
      remark: fd.get('remark') || undefined,
    })
  }

  const defaultTask = task ? `${task.module}.${task.func}` : ''

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>{task ? t('scheduler.editTask') : t('scheduler.createTask')}</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>{t('scheduler.taskName')} *</Label>
            <Input name="name" required defaultValue={task?.name ?? ''} />
          </div>
          <div className="space-y-2">
            <Label>{t('scheduler.taskFunc')} *</Label>
            {registeredTasks.length > 0 ? (
              <Select name="task" defaultValue={defaultTask}>
                <SelectTrigger><SelectValue placeholder={t('scheduler.selectTask')} /></SelectTrigger>
                <SelectContent>
                  {registeredTasks.map((rt) => (
                    <SelectItem key={rt} value={rt}>{rt}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Input name="task" required defaultValue={defaultTask} placeholder="module.func" />
            )}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{t('scheduler.trigger')} *</Label>
              <Select name="trigger" defaultValue={task?.trigger ?? 'cron'}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="cron">Cron</SelectItem>
                  <SelectItem value="interval">Interval</SelectItem>
                  <SelectItem value="date">Date</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>{t('scheduler.triggerArgs')} *</Label>
              <Input name="trigger_args" required defaultValue={task?.trigger_args ?? ''} placeholder="*/5 * * * *" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2"><Label>{t('scheduler.group')}</Label><Input name="group" defaultValue={task?.group ?? 'default'} /></div>
            <div className="space-y-2"><Label>{t('scheduler.maxInstances')}</Label><Input name="max_instances" type="number" defaultValue={task?.max_instances ?? 1} /></div>
          </div>
          <div className="space-y-2"><Label>{t('common.remark')}</Label><Input name="remark" defaultValue={task?.remark ?? ''} /></div>
          <DialogFooter><Button type="submit" disabled={loading}>{loading ? t('common.saving') : t('common.save')}</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
