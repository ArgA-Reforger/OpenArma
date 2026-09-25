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
  const { t } = useI18n()

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t('dataPermission.title')}</h1>
      <div className="flex gap-2 border-b pb-2">
        <Button variant={tab === 'scope' ? 'default' : 'ghost'} size="sm" onClick={() => setTab('scope')}>{t('dataPermission.scope')}</Button>
        <Button variant={tab === 'rule' ? 'default' : 'ghost'} size="sm" onClick={() => setTab('rule')}>{t('dataPermission.rule')}</Button>
      </div>
      {tab === 'scope' ? <ScopeTab /> : <RuleTab />}
    </div>
  )
}

function ScopeTab() {
  const api = useApi()
  const qc = useQueryClient()
  const { t, locale } = useI18n()
  const [page, setPage] = useState(1)
  const [formOpen, setFormOpen] = useState(false)
  const [editScope, setEditScope] = useState<DataScope | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-data-scopes', page],
    queryFn: () => api.get<PageData<DataScope>>(`/sys/data-scopes?page=${page}&size=20`),
  })

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/sys/data-scopes', body),
    onSuccess: () => { toast.success(t('dataPermission.scopeCreated')); qc.invalidateQueries({ queryKey: ['admin-data-scopes'] }); setFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ pk, body }: { pk: number; body: Record<string, unknown> }) => api.put(`/sys/data-scopes/${pk}`, body),
    onSuccess: () => { toast.success(t('dataPermission.scopeUpdated')); qc.invalidateQueries({ queryKey: ['admin-data-scopes'] }); setEditScope(null); setFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (pks: number[]) => api.delete('/sys/data-scopes', { pks }),
    onSuccess: () => { toast.success(t('dataPermission.scopeDeleted')); qc.invalidateQueries({ queryKey: ['admin-data-scopes'] }) },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => { setEditScope(null); setFormOpen(true) }}>{t('dataPermission.createScope')}</Button>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('common.name')}</TableHead><TableHead>{t('common.status')}</TableHead><TableHead>{t('common.remark')}</TableHead><TableHead>{t('common.createdTime')}</TableHead><TableHead className="text-right">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground">{t('common.loading')}</TableCell></TableRow>
            ) : !data?.items?.length ? (
              <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground">{t('common.noData')}</TableCell></TableRow>
            ) : (
              data.items.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-medium">{s.name}</TableCell>
                  <TableCell><Badge variant={s.status === 1 ? 'default' : 'destructive'}>{s.status === 1 ? t('common.enabled') : t('common.disabled')}</Badge></TableCell>
                  <TableCell className="text-muted-foreground">{s.remark ?? '-'}</TableCell>
                  <TableCell className="text-xs">{new Date(s.created_time).toLocaleString(locale)}</TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => { setEditScope(s); setFormOpen(true) }}>{t('common.edit')}</Button>
                    <Button variant="ghost" size="sm" className="text-destructive" onClick={() => deleteMutation.mutate([s.id])}>{t('common.delete')}</Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      {data && data.total_pages > 1 && (
        <div className="flex gap-2 justify-center">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>{t('common.prevPage')}</Button>
          <Button variant="outline" size="sm" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)}>{t('common.nextPage')}</Button>
        </div>
      )}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editScope ? t('dataPermission.editScope') : t('dataPermission.createScope')}</DialogTitle></DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault(); const fd = new FormData(e.currentTarget)
            const body = { name: fd.get('name'), status: Number(fd.get('status')), remark: fd.get('remark') || undefined }
            editScope ? updateMutation.mutate({ pk: editScope.id, body }) : createMutation.mutate(body)
          }} className="space-y-4">
            <div className="space-y-2"><Label>{t('common.name')} *</Label><Input name="name" required defaultValue={editScope?.name ?? ''} /></div>
            <div className="space-y-2"><Label>{t('common.status')}</Label>
              <select name="status" defaultValue={editScope?.status ?? 1} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
                <option value={1}>{t('common.enabled')}</option><option value={0}>{t('common.disabled')}</option>
              </select>
            </div>
            <div className="space-y-2"><Label>{t('common.remark')}</Label><Input name="remark" defaultValue={editScope?.remark ?? ''} /></div>
            <DialogFooter><Button type="submit">{t('common.save')}</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function RuleTab() {
  const api = useApi()
  const qc = useQueryClient()
  const { t } = useI18n()
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
    onSuccess: () => { toast.success(t('dataPermission.ruleCreated')); qc.invalidateQueries({ queryKey: ['admin-data-rules'] }); setFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ pk, body }: { pk: number; body: Record<string, unknown> }) => api.put(`/sys/data-rules/${pk}`, body),
    onSuccess: () => { toast.success(t('dataPermission.ruleUpdated')); qc.invalidateQueries({ queryKey: ['admin-data-rules'] }); setEditRule(null); setFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (pks: number[]) => api.delete('/sys/data-rules', { pks }),
    onSuccess: () => { toast.success(t('dataPermission.ruleDeleted')); qc.invalidateQueries({ queryKey: ['admin-data-rules'] }) },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => { setEditRule(null); setFormOpen(true) }}>{t('dataPermission.createRule')}</Button>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('common.name')}</TableHead><TableHead>{t('dataPermission.model')}</TableHead><TableHead>{t('dataPermission.column')}</TableHead><TableHead>{t('dataPermission.operator')}</TableHead><TableHead>{t('dataPermission.value')}</TableHead><TableHead>{t('common.status')}</TableHead><TableHead className="text-right">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={7} className="text-center py-8 text-muted-foreground">{t('common.loading')}</TableCell></TableRow>
            ) : !data?.items?.length ? (
              <TableRow><TableCell colSpan={7} className="text-center py-8 text-muted-foreground">{t('common.noData')}</TableCell></TableRow>
            ) : (
              data.items.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell className="text-xs">{r.model}</TableCell>
                  <TableCell className="text-xs">{r.column}</TableCell>
                  <TableCell><code className="text-xs bg-muted px-1 rounded">{r.operator}</code></TableCell>
                  <TableCell className="text-xs max-w-32 truncate">{r.value}</TableCell>
                  <TableCell><Badge variant={r.status === 1 ? 'default' : 'destructive'}>{r.status === 1 ? t('common.enabled') : t('common.disabled')}</Badge></TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => { setEditRule(r); setFormOpen(true) }}>{t('common.edit')}</Button>
                    <Button variant="ghost" size="sm" className="text-destructive" onClick={() => deleteMutation.mutate([r.id])}>{t('common.delete')}</Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      {data && data.total_pages > 1 && (
        <div className="flex gap-2 justify-center">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>{t('common.prevPage')}</Button>
          <Button variant="outline" size="sm" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)}>{t('common.nextPage')}</Button>
        </div>
      )}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editRule ? t('dataPermission.editRule') : t('dataPermission.createRule')}</DialogTitle></DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault(); const fd = new FormData(e.currentTarget)
            const body = { name: fd.get('name'), model: fd.get('model'), column: fd.get('column'), operator: fd.get('operator'), expression: fd.get('expression') || undefined, value: fd.get('value'), status: Number(fd.get('status')), remark: fd.get('remark') || undefined }
            editRule ? updateMutation.mutate({ pk: editRule.id, body }) : createMutation.mutate(body)
          }} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>{t('common.name')} *</Label><Input name="name" required defaultValue={editRule?.name ?? ''} /></div>
              <div className="space-y-2"><Label>{t('dataPermission.model')} *</Label>
                {models?.length ? (
                  <select name="model" defaultValue={editRule?.model ?? ''} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm" required>
                    <option value="">{t('dataPermission.selectModel')}</option>
                    {models.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                ) : (
                  <Input name="model" required defaultValue={editRule?.model ?? ''} />
                )}
              </div>
              <div className="space-y-2"><Label>{t('dataPermission.column')} *</Label><Input name="column" required defaultValue={editRule?.column ?? ''} /></div>
              <div className="space-y-2"><Label>{t('dataPermission.operator')} *</Label>
                <select name="operator" defaultValue={editRule?.operator ?? 'eq'} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm" required>
                  {['eq', 'ne', 'gt', 'ge', 'lt', 'le', 'in', 'not_in', 'like', 'not_like'].map((op) => <option key={op} value={op}>{op}</option>)}
                </select>
              </div>
            </div>
            <div className="space-y-2"><Label>{t('dataPermission.value')} *</Label><Input name="value" required defaultValue={editRule?.value ?? ''} /></div>
            <div className="space-y-2"><Label>{t('dataPermission.expression')}</Label><Input name="expression" defaultValue={editRule?.expression ?? ''} /></div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>{t('common.status')}</Label>
                <select name="status" defaultValue={editRule?.status ?? 1} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
                  <option value={1}>{t('common.enabled')}</option><option value={0}>{t('common.disabled')}</option>
                </select>
              </div>
              <div className="space-y-2"><Label>{t('common.remark')}</Label><Input name="remark" defaultValue={editRule?.remark ?? ''} /></div>
            </div>
            <DialogFooter><Button type="submit">{t('common.save')}</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
