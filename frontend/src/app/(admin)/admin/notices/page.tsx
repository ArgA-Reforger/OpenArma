'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
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

const NOTICE_TYPES: Record<number, string> = { 1: '通知', 2: '公告' }

export default function NoticesPage() {
  const api = useApi()
  const qc = useQueryClient()
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
    onSuccess: () => { toast.success('通知创建成功'); qc.invalidateQueries({ queryKey: ['admin-notices'] }); setFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ pk, body }: { pk: number; body: Record<string, unknown> }) => api.put(`/sys/notices/${pk}`, body),
    onSuccess: () => { toast.success('通知更新成功'); qc.invalidateQueries({ queryKey: ['admin-notices'] }); setEditNotice(null); setFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (pks: number[]) => api.delete('/sys/notices', { pks }),
    onSuccess: () => { toast.success('已删除'); qc.invalidateQueries({ queryKey: ['admin-notices'] }); setDeleteIds([]) },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">通知管理</h1>
        <Button onClick={() => { setEditNotice(null); setFormOpen(true) }}>新增通知</Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>标题</TableHead>
              <TableHead>类型</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>创建时间</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground">加载中...</TableCell></TableRow>
            ) : !data?.items?.length ? (
              <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground">暂无数据</TableCell></TableRow>
            ) : (
              data.items.map((n) => (
                <TableRow key={n.id}>
                  <TableCell className="font-medium">{n.title}</TableCell>
                  <TableCell><Badge variant="secondary">{NOTICE_TYPES[n.type] ?? n.type}</Badge></TableCell>
                  <TableCell>
                    <Badge variant={n.status === 1 ? 'default' : 'destructive'}>
                      {n.status === 1 ? '启用' : '禁用'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs">{new Date(n.created_time).toLocaleString('zh-CN')}</TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => setPreviewNotice(n)}>预览</Button>
                    <Button variant="ghost" size="sm" onClick={() => { setEditNotice(n); setFormOpen(true) }}>编辑</Button>
                    <Button variant="ghost" size="sm" className="text-destructive" onClick={() => setDeleteIds([n.id])}>删除</Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">共 {data.total} 条</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>上一页</Button>
            <Button variant="outline" size="sm" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)}>下一页</Button>
          </div>
        </div>
      )}

      {/* Form */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>{editNotice ? '编辑通知' : '新增通知'}</DialogTitle></DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault()
            const fd = new FormData(e.currentTarget)
            const body = { title: fd.get('title'), type: Number(fd.get('type')), status: Number(fd.get('status')), content: fd.get('content') }
            editNotice ? updateMutation.mutate({ pk: editNotice.id, body }) : createMutation.mutate(body)
          }} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>标题 *</Label><Input name="title" required defaultValue={editNotice?.title ?? ''} /></div>
              <div className="space-y-2"><Label>类型</Label>
                <select name="type" defaultValue={editNotice?.type ?? 1} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
                  <option value={1}>通知</option><option value={2}>公告</option>
                </select>
              </div>
            </div>
            <div className="space-y-2"><Label>状态</Label>
              <select name="status" defaultValue={editNotice?.status ?? 1} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
                <option value={1}>启用</option><option value={0}>禁用</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>内容 *</Label>
              <Textarea name="content" required rows={10} defaultValue={editNotice?.content ?? ''} placeholder="支持 Markdown 格式" />
            </div>
            <DialogFooter><Button type="submit">保存</Button></DialogFooter>
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
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>确定要删除选中的通知吗？</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteMutation.mutate(deleteIds)}>删除</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
