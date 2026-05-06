'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
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
      toast.success('日志已删除')
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
        <h1 className="text-2xl font-bold">操作日志</h1>
        {selected.size > 0 && (
          <Button variant="destructive" size="sm" onClick={() => setConfirmDelete(true)}>
            删除选中 ({selected.size})
          </Button>
        )}
      </div>

      <Input
        placeholder="搜索用户名..."
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
              <TableHead>用户</TableHead>
              <TableHead>方法</TableHead>
              <TableHead>路径</TableHead>
              <TableHead>状态码</TableHead>
              <TableHead>耗时</TableHead>
              <TableHead>IP</TableHead>
              <TableHead>时间</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">加载中...</TableCell>
              </TableRow>
            ) : !data?.items?.length ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">暂无数据</TableCell>
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
                  <TableCell className="text-xs">{new Date(log.opera_time).toLocaleString('zh-CN')}</TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => setDetail(log)}>详情</Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">共 {data.total} 条，第 {data.page}/{data.total_pages} 页</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>上一页</Button>
            <Button variant="outline" size="sm" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)}>下一页</Button>
          </div>
        </div>
      )}

      <Dialog open={!!detail} onOpenChange={(open) => !open && setDetail(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>操作日志详情</DialogTitle>
          </DialogHeader>
          {detail && (
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Trace ID" value={detail.trace_id} />
                <Field label="用户" value={detail.username} />
                <Field label="方法" value={detail.method} />
                <Field label="路径" value={detail.path} />
                <Field label="状态码" value={detail.code} />
                <Field label="耗时" value={`${detail.cost_time}ms`} />
                <Field label="IP" value={detail.ip} />
                <Field label="地区" value={[detail.country, detail.region, detail.city].filter(Boolean).join(' ')} />
                <Field label="浏览器" value={detail.browser} />
                <Field label="操作系统" value={detail.os} />
                <Field label="设备" value={detail.device} />
                <Field label="时间" value={new Date(detail.opera_time).toLocaleString('zh-CN')} />
              </div>
              {detail.msg && <Field label="消息" value={detail.msg} />}
              {detail.args && (
                <div>
                  <span className="text-muted-foreground">请求参数</span>
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
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>确定要删除选中的 {selected.size} 条日志吗？</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteMutation.mutate(Array.from(selected))}>删除</AlertDialogAction>
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
