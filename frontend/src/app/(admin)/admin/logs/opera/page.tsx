'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'

interface OperaLog {
  id: number
  trace_id: string
  username: string | null
  method: string
  title: string
  path: string
  ip: string
  country: string | null
  region: string | null
  city: string | null
  user_agent: string | null
  os: string | null
  browser: string | null
  device: string | null
  args: Record<string, unknown> | null
  status: number
  code: string
  msg: string | null
  cost_time: number
  opera_time: string
}

interface PageData<T> {
  items: T[]
  total: number
  page: number
  size: number
  total_pages: number
}

export default function OperaLogPage() {
  const api = useApi()
  const qc = useQueryClient()
  const { t, locale } = useI18n()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [detail, setDetail] = useState<OperaLog | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-opera-logs', page, search],
    queryFn: () =>
      api.get<PageData<OperaLog>>(
        `/logs/opera?page=${page}&size=20${search ? `&username=${search}` : ''}`,
      ),
  })

  const deleteMutation = useMutation({
    mutationFn: (pks: number[]) => api.delete('/logs/opera', { pks }),
    onSuccess: () => {
      toast.success(t('log.logDeleted'))
      qc.invalidateQueries({ queryKey: ['admin-opera-logs'] })
      setSelected(new Set())
      setConfirmDelete(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function toggleAll() {
    if (!data?.items) return
    setSelected(selected.size === data.items.length ? new Set() : new Set(data.items.map((i) => i.id)))
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('log.operaLog')}</h1>
        {selected.size > 0 && (
          <Button variant="destructive" size="sm" onClick={() => setConfirmDelete(true)}>
            {t('log.deleteSelected', { count: selected.size })}
          </Button>
        )}
      </div>

      <Input
        placeholder={t('log.searchUsername')}
        value={search}
        onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        className="max-w-xs"
      />

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <Checkbox
                  checked={!!data?.items?.length && selected.size === data.items.length}
                  onCheckedChange={toggleAll}
                />
              </TableHead>
              <TableHead>{t('log.user')}</TableHead>
              <TableHead>{t('log.method')}</TableHead>
              <TableHead>{t('log.path')}</TableHead>
              <TableHead>{t('log.statusCode')}</TableHead>
              <TableHead>{t('log.costTime')}</TableHead>
              <TableHead>{t('log.ip')}</TableHead>
              <TableHead>{t('log.time')}</TableHead>
              <TableHead className="text-right">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">{t('common.loading')}</TableCell>
              </TableRow>
            ) : !data?.items?.length ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">{t('common.noData')}</TableCell>
              </TableRow>
            ) : (
              data.items.map((log) => (
                <TableRow key={log.id}>
                  <TableCell>
                    <Checkbox checked={selected.has(log.id)} onCheckedChange={() => toggleSelect(log.id)} />
                  </TableCell>
                  <TableCell className="font-medium">{log.username ?? '-'}</TableCell>
                  <TableCell>
                    <Badge variant={log.method === 'GET' ? 'secondary' : log.method === 'DELETE' ? 'destructive' : 'default'}>
                      {log.method}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs max-w-48 truncate">{log.path}</TableCell>
                  <TableCell>
                    <Badge variant={log.code === '200' ? 'default' : 'destructive'}>{log.code}</Badge>
                  </TableCell>
                  <TableCell className="text-xs">{log.cost_time}ms</TableCell>
                  <TableCell className="text-xs">{log.ip}</TableCell>
                  <TableCell className="text-xs">{new Date(log.opera_time).toLocaleString(locale)}</TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => setDetail(log)}>{t('log.detail')}</Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">{t('common.total', { total: data.total })}, {t('common.pageInfo', { page: data.page, totalPages: data.total_pages })}</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>{t('common.prevPage')}</Button>
            <Button variant="outline" size="sm" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)}>{t('common.nextPage')}</Button>
          </div>
        </div>
      )}

      <Dialog open={!!detail} onOpenChange={(open) => !open && setDetail(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('log.detailTitle')}</DialogTitle>
          </DialogHeader>
          {detail && (
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Trace ID" value={detail.trace_id} />
                <Field label={t('log.user')} value={detail.username} />
                <Field label={t('log.method')} value={detail.method} />
                <Field label={t('log.path')} value={detail.path} />
                <Field label={t('log.statusCode')} value={detail.code} />
                <Field label={t('log.costTime')} value={`${detail.cost_time}ms`} />
                <Field label={t('log.ip')} value={detail.ip} />
                <Field label={t('log.region')} value={[detail.country, detail.region, detail.city].filter(Boolean).join(' ')} />
                <Field label={t('log.browser')} value={detail.browser} />
                <Field label={t('log.os')} value={detail.os} />
                <Field label={t('log.device')} value={detail.device} />
                <Field label={t('log.time')} value={new Date(detail.opera_time).toLocaleString(locale)} />
              </div>
              {detail.msg && <Field label={t('log.message')} value={detail.msg} />}
              {detail.args && (
                <div>
                  <span className="text-muted-foreground">{t('log.requestParams')}</span>
                  <pre className="mt-1 rounded bg-muted p-3 text-xs overflow-x-auto">
                    {JSON.stringify(detail.args, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('common.confirmDelete')}</AlertDialogTitle>
            <AlertDialogDescription>{t('log.confirmDelete', { count: selected.size })}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteMutation.mutate(Array.from(selected))}>{t('common.delete')}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <span className="text-muted-foreground">{label}</span>
      <p className="font-medium break-all">{value || '-'}</p>
    </div>
  )
}
