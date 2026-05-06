'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
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
import { toast } from 'sonner'

interface DataScope {
  id: number
  name: string
  status: number
  remark: string | null
  created_time: string
}

interface DataRule {
  id: number
  name: string
  model: string
  column: string
  operator: string
  expression: string
  value: string
  status: number
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

export default function DataPermissionPage() {
  const [tab, setTab] = useState<'scope' | 'rule'>('scope')

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">数据权限</h1>
      <div className="flex gap-2 border-b pb-2">
        <Button variant={tab === 'scope' ? 'default' : 'ghost'} size="sm" onClick={() => setTab('scope')}>数据范围</Button>
        <Button variant={tab === 'rule' ? 'default' : 'ghost'} size="sm" onClick={() => setTab('rule')}>数据规则</Button>
      </div>
      {tab === 'scope' ? <ScopeTab /> : <RuleTab />}
    </div>
  )
}

function ScopeTab() {
  const api = useApi()
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [formOpen, setFormOpen] = useState(false)
  const [editScope, setEditScope] = useState<DataScope | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-data-scopes', page],
    queryFn: () => api.get<PageData<DataScope>>(`/sys/data-scopes?page=${page}&size=20`),
  })

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/sys/data-scopes', body),
    onSuccess: () => { toast.success('数据范围创建成功'); qc.invalidateQueries({ queryKey: ['admin-data-scopes'] }); setFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ pk, body }: { pk: number; body: Record<string, unknown> }) => api.put(`/sys/data-scopes/${pk}`, body),
    onSuccess: () => { toast.success('数据范围更新成功'); qc.invalidateQueries({ queryKey: ['admin-data-scopes'] }); setEditScope(null); setFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (pks: number[]) => api.delete('/sys/data-scopes', { pks }),
    onSuccess: () => { toast.success('已删除'); qc.invalidateQueries({ queryKey: ['admin-data-scopes'] }) },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => { setEditScope(null); setFormOpen(true) }}>新增数据范围</Button>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>名称</TableHead><TableHead>状态</TableHead><TableHead>备注</TableHead><TableHead>创建时间</TableHead><TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground">加载中...</TableCell></TableRow>
            ) : !data?.items?.length ? (
              <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground">暂无数据</TableCell></TableRow>
            ) : (
              data.items.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-medium">{s.name}</TableCell>
                  <TableCell><Badge variant={s.status === 1 ? 'default' : 'destructive'}>{s.status === 1 ? '启用' : '禁用'}</Badge></TableCell>
                  <TableCell className="text-muted-foreground">{s.remark ?? '-'}</TableCell>
                  <TableCell className="text-xs">{new Date(s.created_time).toLocaleString('zh-CN')}</TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => { setEditScope(s); setFormOpen(true) }}>编辑</Button>
                    <Button variant="ghost" size="sm" className="text-destructive" onClick={() => deleteMutation.mutate([s.id])}>删除</Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      {data && data.total_pages > 1 && (
        <div className="flex gap-2 justify-center">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>上一页</Button>
          <Button variant="outline" size="sm" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)}>下一页</Button>
        </div>
      )}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editScope ? '编辑数据范围' : '新增数据范围'}</DialogTitle></DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault(); const fd = new FormData(e.currentTarget)
            const body = { name: fd.get('name'), status: Number(fd.get('status')), remark: fd.get('remark') || undefined }
            editScope ? updateMutation.mutate({ pk: editScope.id, body }) : createMutation.mutate(body)
          }} className="space-y-4">
            <div className="space-y-2"><Label>名称 *</Label><Input name="name" required defaultValue={editScope?.name ?? ''} /></div>
            <div className="space-y-2"><Label>状态</Label>
              <select name="status" defaultValue={editScope?.status ?? 1} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
                <option value={1}>启用</option><option value={0}>禁用</option>
              </select>
            </div>
            <div className="space-y-2"><Label>备注</Label><Input name="remark" defaultValue={editScope?.remark ?? ''} /></div>
            <DialogFooter><Button type="submit">保存</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function RuleTab() {
  const api = useApi()
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [formOpen, setFormOpen] = useState(false)
  const [editRule, setEditRule] = useState<DataRule | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-data-rules', page],
    queryFn: () => api.get<PageData<DataRule>>(`/sys/data-rules?page=${page}&size=20`),
  })

  const { data: models } = useQuery({
    queryKey: ['admin-data-rule-models'],
    queryFn: () => api.get<string[]>('/sys/data-rules/models'),
  })

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/sys/data-rules', body),
    onSuccess: () => { toast.success('数据规则创建成功'); qc.invalidateQueries({ queryKey: ['admin-data-rules'] }); setFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ pk, body }: { pk: number; body: Record<string, unknown> }) => api.put(`/sys/data-rules/${pk}`, body),
    onSuccess: () => { toast.success('数据规则更新成功'); qc.invalidateQueries({ queryKey: ['admin-data-rules'] }); setEditRule(null); setFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (pks: number[]) => api.delete('/sys/data-rules', { pks }),
    onSuccess: () => { toast.success('已删除'); qc.invalidateQueries({ queryKey: ['admin-data-rules'] }) },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => { setEditRule(null); setFormOpen(true) }}>新增数据规则</Button>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>名称</TableHead><TableHead>模型</TableHead><TableHead>列</TableHead><TableHead>操作符</TableHead><TableHead>值</TableHead><TableHead>状态</TableHead><TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={7} className="text-center py-8 text-muted-foreground">加载中...</TableCell></TableRow>
            ) : !data?.items?.length ? (
              <TableRow><TableCell colSpan={7} className="text-center py-8 text-muted-foreground">暂无数据</TableCell></TableRow>
            ) : (
              data.items.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell className="text-xs">{r.model}</TableCell>
                  <TableCell className="text-xs">{r.column}</TableCell>
                  <TableCell><code className="text-xs bg-muted px-1 rounded">{r.operator}</code></TableCell>
                  <TableCell className="text-xs max-w-32 truncate">{r.value}</TableCell>
                  <TableCell><Badge variant={r.status === 1 ? 'default' : 'destructive'}>{r.status === 1 ? '启用' : '禁用'}</Badge></TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => { setEditRule(r); setFormOpen(true) }}>编辑</Button>
                    <Button variant="ghost" size="sm" className="text-destructive" onClick={() => deleteMutation.mutate([r.id])}>删除</Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      {data && data.total_pages > 1 && (
        <div className="flex gap-2 justify-center">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>上一页</Button>
          <Button variant="outline" size="sm" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)}>下一页</Button>
        </div>
      )}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editRule ? '编辑数据规则' : '新增数据规则'}</DialogTitle></DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault(); const fd = new FormData(e.currentTarget)
            const body = { name: fd.get('name'), model: fd.get('model'), column: fd.get('column'), operator: fd.get('operator'), expression: fd.get('expression') || undefined, value: fd.get('value'), status: Number(fd.get('status')), remark: fd.get('remark') || undefined }
            editRule ? updateMutation.mutate({ pk: editRule.id, body }) : createMutation.mutate(body)
          }} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>名称 *</Label><Input name="name" required defaultValue={editRule?.name ?? ''} /></div>
              <div className="space-y-2"><Label>模型 *</Label>
                {models?.length ? (
                  <select name="model" defaultValue={editRule?.model ?? ''} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm" required>
                    <option value="">选择模型</option>
                    {models.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                ) : (
                  <Input name="model" required defaultValue={editRule?.model ?? ''} />
                )}
              </div>
              <div className="space-y-2"><Label>列 *</Label><Input name="column" required defaultValue={editRule?.column ?? ''} /></div>
              <div className="space-y-2"><Label>操作符 *</Label>
                <select name="operator" defaultValue={editRule?.operator ?? 'eq'} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm" required>
                  {['eq', 'ne', 'gt', 'ge', 'lt', 'le', 'in', 'not_in', 'like', 'not_like'].map((op) => <option key={op} value={op}>{op}</option>)}
                </select>
              </div>
            </div>
            <div className="space-y-2"><Label>值 *</Label><Input name="value" required defaultValue={editRule?.value ?? ''} /></div>
            <div className="space-y-2"><Label>表达式</Label><Input name="expression" defaultValue={editRule?.expression ?? ''} /></div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>状态</Label>
                <select name="status" defaultValue={editRule?.status ?? 1} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
                  <option value={1}>启用</option><option value={0}>禁用</option>
                </select>
              </div>
              <div className="space-y-2"><Label>备注</Label><Input name="remark" defaultValue={editRule?.remark ?? ''} /></div>
            </div>
            <DialogFooter><Button type="submit">保存</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
