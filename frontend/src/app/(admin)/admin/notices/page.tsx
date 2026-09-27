'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'

interface Notice {
  id: number
  title: string
  type: number
  status: number
  content: string
  created_time: string
  updated_time: string | null
}

interface PageData<T> {
  items: T[]
  total: number
  page: number
  size: number
  total_pages: number
}

export default function NoticesPage() {
  const api = useApi()
  const qc = useQueryClient()
  const { t, locale } = useI18n()
  const NOTICE_TYPES: Record<number, string> = { 1: t('notice.typeNotice'), 2: t('notice.typeAnnouncement') }
  const [page, setPage] = useState(1)
  const [formOpen, setFormOpen] = useState(false)
  const [editNotice, setEditNotice] = useState<Notice | null>(null)
  const [previewNotice, setPreviewNotice] = useState<Notice | null>(null)
  const [deleteIds, setDeleteIds] = useState<number[]>([])

  const { data, isLoading } = useQuery({
    queryKey: ['admin-notices', page],
    queryFn: () => api.get<PageData<Notice>>(`/sys/notices?page=${page}&size=20`),
  })

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/sys/notices', body),
    onSuccess: () => { toast.success(t('notice.noticeCreated')); qc.invalidateQueries({ queryKey: ['admin-notices'] }); setFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ pk, body }: { pk: number; body: Record<string, unknown> }) => api.put(`/sys/notices/${pk}`, body),
    onSuccess: () => { toast.success(t('notice.noticeUpdated')); qc.invalidateQueries({ queryKey: ['admin-notices'] }); setEditNotice(null); setFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (pks: number[]) => api.delete('/sys/notices', { pks }),
    onSuccess: () => { toast.success(t('notice.noticeDeleted')); qc.invalidateQueries({ queryKey: ['admin-notices'] }); setDeleteIds([]) },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('notice.title')}</h1>
        <Button onClick={() => { setEditNotice(null); setFormOpen(true) }}>{t('notice.createNotice')}</Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('notice.noticeTitle')}</TableHead>
              <TableHead>{t('notice.type')}</TableHead>
              <TableHead>{t('common.status')}</TableHead>
              <TableHead>{t('common.createdTime')}</TableHead>
              <TableHead className="text-right">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground">{t('common.loading')}</TableCell></TableRow>
            ) : !data?.items?.length ? (
              <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground">{t('common.noData')}</TableCell></TableRow>
            ) : (
              data.items.map((n) => (
                <TableRow key={n.id}>
                  <TableCell className="font-medium">{n.title}</TableCell>
                  <TableCell><Badge variant="secondary">{NOTICE_TYPES[n.type] ?? n.type}</Badge></TableCell>
                  <TableCell>
                    <Badge variant={n.status === 1 ? 'default' : 'destructive'}>
                      {n.status === 1 ? t('common.enabled') : t('common.disabled')}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs">{new Date(n.created_time).toLocaleString(locale)}</TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => setPreviewNotice(n)}>{t('common.preview')}</Button>
                    <Button variant="ghost" size="sm" onClick={() => { setEditNotice(n); setFormOpen(true) }}>{t('common.edit')}</Button>
                    <Button variant="ghost" size="sm" className="text-destructive" onClick={() => setDeleteIds([n.id])}>{t('common.delete')}</Button>
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

      {/* Form */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>{editNotice ? t('notice.editNotice') : t('notice.createNotice')}</DialogTitle></DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault()
            const fd = new FormData(e.currentTarget)
            const body = { title: fd.get('title'), type: Number(fd.get('type')), status: Number(fd.get('status')), content: fd.get('content') }
            editNotice ? updateMutation.mutate({ pk: editNotice.id, body }) : createMutation.mutate(body)
          }} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>{t('notice.noticeTitle')} *</Label><Input name="title" required defaultValue={editNotice?.title ?? ''} /></div>
              <div className="space-y-2"><Label>{t('notice.type')}</Label>
                <select name="type" defaultValue={editNotice?.type ?? 1} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
                  <option value={1}>{t('notice.typeNotice')}</option><option value={2}>{t('notice.typeAnnouncement')}</option>
                </select>
              </div>
            </div>
            <div className="space-y-2"><Label>{t('common.status')}</Label>
              <select name="status" defaultValue={editNotice?.status ?? 1} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
                <option value={1}>{t('common.enabled')}</option><option value={0}>{t('common.disabled')}</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>{t('notice.content')} *</Label>
              <Textarea name="content" required rows={10} defaultValue={editNotice?.content ?? ''} placeholder={t('notice.markdownSupport')} />
            </div>
            <DialogFooter><Button type="submit">{t('common.save')}</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Preview */}
      <Dialog open={!!previewNotice} onOpenChange={(open) => !open && setPreviewNotice(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{previewNotice?.title}</DialogTitle></DialogHeader>
          <div className="prose prose-sm max-w-none whitespace-pre-wrap">{previewNotice?.content}</div>
        </DialogContent>
      </Dialog>

      {/* Delete */}
      <AlertDialog open={deleteIds.length > 0} onOpenChange={(open) => !open && setDeleteIds([])}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('common.confirmDelete')}</AlertDialogTitle>
            <AlertDialogDescription>{t('notice.confirmDelete')}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteMutation.mutate(deleteIds)}>{t('common.delete')}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
