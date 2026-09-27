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
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'

interface LoginLog {
  id: number
  username: string
  status: number
  ip: string
  country: string | null
  region: string | null
  city: string | null
  user_agent: string | null
  os: string | null
  browser: string | null
  device: string | null
  msg: string | null
  login_time: string
}

interface PageData<T> {
  items: T[]
  total: number
  page: number
  size: number
  total_pages: number
}

export default function LoginLogPage() {
  const api = useApi()
  const qc = useQueryClient()
  const { t, locale } = useI18n()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [confirmDelete, setConfirmDelete] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-login-logs', page, search],
    queryFn: () =>
      api.get<PageData<LoginLog>>(
        `/logs/login?page=${page}&size=20${search ? `&username=${search}` : ''}`,
      ),
  })

  const deleteMutation = useMutation({
    mutationFn: (pks: number[]) => api.delete('/logs/login', { pks }),
    onSuccess: () => {
      toast.success(t('log.logDeleted'))
      qc.invalidateQueries({ queryKey: ['admin-login-logs'] })
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
    if (selected.size === data.items.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(data.items.map((i) => i.id)))
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('log.loginLog')}</h1>
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
              <TableHead>{t('user.username')}</TableHead>
              <TableHead>{t('common.status')}</TableHead>
              <TableHead>{t('log.ip')}</TableHead>
              <TableHead>{t('log.region')}</TableHead>
              <TableHead>{t('log.browser')}</TableHead>
              <TableHead>{t('log.os')}</TableHead>
              <TableHead>{t('log.message')}</TableHead>
              <TableHead>{t('log.loginTime')}</TableHead>
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
                  <TableCell className="font-medium">{log.username}</TableCell>
                  <TableCell>
                    <Badge variant={log.status === 1 ? 'default' : 'destructive'}>
                      {log.status === 1 ? t('log.success') : t('log.failed')}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs">{log.ip}</TableCell>
                  <TableCell className="text-xs">{[log.country, log.region, log.city].filter(Boolean).join(' ') || '-'}</TableCell>
                  <TableCell className="text-xs">{log.browser ?? '-'}</TableCell>
                  <TableCell className="text-xs">{log.os ?? '-'}</TableCell>
                  <TableCell className="text-xs text-muted-foreground max-w-40 truncate">{log.msg ?? '-'}</TableCell>
                  <TableCell className="text-xs">{new Date(log.login_time).toLocaleString(locale)}</TableCell>
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
