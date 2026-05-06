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

interface DictType {
  id: number
  name: string
  code: string
  status: number
  remark: string | null
  created_time: string
}

interface DictData {
  id: number
  type_id: number
  label: string
  value: string
  sort: number
  status: number
  remark: string | null
}

interface PageData<T> {
  items: T[]
  total: number
  page: number
  size: number
  total_pages: number
}

export default function DictPage() {
  const api = useApi()
  const qc = useQueryClient()
  const [selectedType, setSelectedType] = useState<DictType | null>(null)
  const [typeFormOpen, setTypeFormOpen] = useState(false)
  const [editType, setEditType] = useState<DictType | null>(null)
  const [dataFormOpen, setDataFormOpen] = useState(false)
  const [editData, setEditData] = useState<DictData | null>(null)
  const [typePage, setTypePage] = useState(1)
  const [dataPage, setDataPage] = useState(1)

  const { data: types, isLoading: typesLoading } = useQuery({
    queryKey: ['admin-dict-types', typePage],
    queryFn: () => api.get<PageData<DictType>>(`/sys/dict-types?page=${typePage}&size=20`),
  })

  const { data: dictData, isLoading: dataLoading } = useQuery({
    queryKey: ['admin-dict-data', selectedType?.id, dataPage],
    queryFn: () =>
      api.get<PageData<DictData>>(`/sys/dict-datas?page=${dataPage}&size=20&type_id=${selectedType!.id}`),
    enabled: !!selectedType,
  })

  const createTypeMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/sys/dict-types', body),
    onSuccess: () => { toast.success('字典类型创建成功'); qc.invalidateQueries({ queryKey: ['admin-dict-types'] }); setTypeFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const updateTypeMutation = useMutation({
    mutationFn: ({ pk, body }: { pk: number; body: Record<string, unknown> }) => api.put(`/sys/dict-types/${pk}`, body),
    onSuccess: () => { toast.success('字典类型更新成功'); qc.invalidateQueries({ queryKey: ['admin-dict-types'] }); setEditType(null); setTypeFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteTypeMutation = useMutation({
    mutationFn: (pks: number[]) => api.delete('/sys/dict-types', { pks }),
    onSuccess: () => { toast.success('已删除'); qc.invalidateQueries({ queryKey: ['admin-dict-types'] }); if (selectedType) setSelectedType(null) },
    onError: (e: Error) => toast.error(e.message),
  })

  const createDataMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/sys/dict-datas', body),
    onSuccess: () => { toast.success('字典数据创建成功'); qc.invalidateQueries({ queryKey: ['admin-dict-data'] }); setDataFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const updateDataMutation = useMutation({
    mutationFn: ({ pk, body }: { pk: number; body: Record<string, unknown> }) => api.put(`/sys/dict-datas/${pk}`, body),
    onSuccess: () => { toast.success('字典数据更新成功'); qc.invalidateQueries({ queryKey: ['admin-dict-data'] }); setEditData(null); setDataFormOpen(false) },
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteDataMutation = useMutation({
    mutationFn: (pks: number[]) => api.delete('/sys/dict-datas', { pks }),
    onSuccess: () => { toast.success('已删除'); qc.invalidateQueries({ queryKey: ['admin-dict-data'] }) },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">字典管理</h1>

      <div className="grid grid-cols-5 gap-6">
        {/* Left: Dict Types */}
        <div className="col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">字典类型</h2>
            <Button size="sm" onClick={() => { setEditType(null); setTypeFormOpen(true) }}>新增</Button>
          </div>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>编码</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {typesLoading ? (
                  <TableRow><TableCell colSpan={4} className="text-center py-6 text-muted-foreground">加载中...</TableCell></TableRow>
                ) : !types?.items?.length ? (
                  <TableRow><TableCell colSpan={4} className="text-center py-6 text-muted-foreground">暂无数据</TableCell></TableRow>
                ) : (
                  types.items.map((t) => (
                    <TableRow
                      key={t.id}
                      className={`cursor-pointer ${selectedType?.id === t.id ? 'bg-accent' : ''}`}
                      onClick={() => { setSelectedType(t); setDataPage(1) }}
                    >
                      <TableCell className="font-medium">{t.name}</TableCell>
                      <TableCell><code className="text-xs bg-muted px-1 rounded">{t.code}</code></TableCell>
                      <TableCell>
                        <Badge variant={t.status === 1 ? 'default' : 'destructive'} className="text-xs">
                          {t.status === 1 ? '启用' : '禁用'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); setEditType(t); setTypeFormOpen(true) }}>编辑</Button>
                        <Button variant="ghost" size="sm" className="text-destructive" onClick={(e) => { e.stopPropagation(); deleteTypeMutation.mutate([t.id]) }}>删除</Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
          {types && types.total_pages > 1 && (
            <div className="flex gap-2 justify-center">
              <Button variant="outline" size="sm" disabled={typePage <= 1} onClick={() => setTypePage((p) => p - 1)}>上一页</Button>
              <Button variant="outline" size="sm" disabled={typePage >= types.total_pages} onClick={() => setTypePage((p) => p + 1)}>下一页</Button>
            </div>
          )}
        </div>

        {/* Right: Dict Data */}
        <div className="col-span-3 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              {selectedType ? `${selectedType.name} - 字典数据` : '请选择字典类型'}
            </h2>
            {selectedType && (
              <Button size="sm" onClick={() => { setEditData(null); setDataFormOpen(true) }}>新增</Button>
            )}
          </div>
          {selectedType ? (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>标签</TableHead>
                      <TableHead>值</TableHead>
                      <TableHead>排序</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead className="text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dataLoading ? (
                      <TableRow><TableCell colSpan={5} className="text-center py-6 text-muted-foreground">加载中...</TableCell></TableRow>
                    ) : !dictData?.items?.length ? (
                      <TableRow><TableCell colSpan={5} className="text-center py-6 text-muted-foreground">暂无数据</TableCell></TableRow>
                    ) : (
                      dictData.items.map((d) => (
                        <TableRow key={d.id}>
                          <TableCell className="font-medium">{d.label}</TableCell>
                          <TableCell><code className="text-xs bg-muted px-1 rounded">{d.value}</code></TableCell>
                          <TableCell>{d.sort}</TableCell>
                          <TableCell>
                            <Badge variant={d.status === 1 ? 'default' : 'destructive'} className="text-xs">
                              {d.status === 1 ? '启用' : '禁用'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="sm" onClick={() => { setEditData(d); setDataFormOpen(true) }}>编辑</Button>
                            <Button variant="ghost" size="sm" className="text-destructive" onClick={() => deleteDataMutation.mutate([d.id])}>删除</Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
              {dictData && dictData.total_pages > 1 && (
                <div className="flex gap-2 justify-center">
                  <Button variant="outline" size="sm" disabled={dataPage <= 1} onClick={() => setDataPage((p) => p - 1)}>上一页</Button>
                  <Button variant="outline" size="sm" disabled={dataPage >= dictData.total_pages} onClick={() => setDataPage((p) => p + 1)}>下一页</Button>
                </div>
              )}
            </>
          ) : (
            <div className="rounded-md border p-12 text-center text-muted-foreground">点击左侧字典类型查看数据</div>
          )}
        </div>
      </div>

      {/* Type Form */}
      <Dialog open={typeFormOpen} onOpenChange={setTypeFormOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editType ? '编辑字典类型' : '新增字典类型'}</DialogTitle></DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault()
            const fd = new FormData(e.currentTarget)
            const body = { name: fd.get('name'), code: fd.get('code'), status: Number(fd.get('status')), remark: fd.get('remark') || undefined }
            editType ? updateTypeMutation.mutate({ pk: editType.id, body }) : createTypeMutation.mutate(body)
          }} className="space-y-4">
            <div className="space-y-2"><Label>名称 *</Label><Input name="name" required defaultValue={editType?.name ?? ''} /></div>
            <div className="space-y-2"><Label>编码 *</Label><Input name="code" required defaultValue={editType?.code ?? ''} pattern="^[A-Z_]+$" title="仅大写字母和下划线" /></div>
            <div className="space-y-2"><Label>状态</Label>
              <select name="status" defaultValue={editType?.status ?? 1} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
                <option value={1}>启用</option><option value={0}>禁用</option>
              </select>
            </div>
            <div className="space-y-2"><Label>备注</Label><Input name="remark" defaultValue={editType?.remark ?? ''} /></div>
            <DialogFooter><Button type="submit">保存</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Data Form */}
      <Dialog open={dataFormOpen} onOpenChange={setDataFormOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editData ? '编辑字典数据' : '新增字典数据'}</DialogTitle></DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault()
            const fd = new FormData(e.currentTarget)
            const body = {
              type_id: selectedType!.id,
              label: fd.get('label'),
              value: fd.get('value'),
              sort: Number(fd.get('sort') || 0),
              status: Number(fd.get('status')),
              remark: fd.get('remark') || undefined,
            }
            editData ? updateDataMutation.mutate({ pk: editData.id, body }) : createDataMutation.mutate(body)
          }} className="space-y-4">
            <div className="space-y-2"><Label>标签 *</Label><Input name="label" required defaultValue={editData?.label ?? ''} /></div>
            <div className="space-y-2"><Label>值 *</Label><Input name="value" required defaultValue={editData?.value ?? ''} /></div>
            <div className="space-y-2"><Label>排序</Label><Input name="sort" type="number" defaultValue={editData?.sort ?? 0} /></div>
            <div className="space-y-2"><Label>状态</Label>
              <select name="status" defaultValue={editData?.status ?? 1} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm">
                <option value={1}>启用</option><option value={0}>禁用</option>
              </select>
            </div>
            <div className="space-y-2"><Label>备注</Label><Input name="remark" defaultValue={editData?.remark ?? ''} /></div>
            <DialogFooter><Button type="submit">保存</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
