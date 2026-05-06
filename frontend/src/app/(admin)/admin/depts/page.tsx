'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'

interface DeptNode {
  id: number
  name: string
  parent_id: number | null
  sort: number
  leader: string | null
  phone: string | null
  email: string | null
  status: number
  children?: DeptNode[]
  created_time: string
}

export default function DeptsPage() {
  const api = useApi()
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editDept, setEditDept] = useState<DeptNode | null>(null)
  const [deleteDept, setDeleteDept] = useState<DeptNode | null>(null)
  const [parentId, setParentId] = useState<number | null>(null)

  const { data: deptTree, isLoading } = useQuery({
    queryKey: ['admin-depts', search],
    queryFn: () =>
      api.get<DeptNode[]>(`/sys/depts${search ? `?name=${search}` : ''}`),
  })

  const flatDepts = flattenTree(deptTree ?? [])

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/sys/depts', body),
    onSuccess: () => {
      toast.success('部门创建成功')
      qc.invalidateQueries({ queryKey: ['admin-depts'] })
      setFormOpen(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ pk, body }: { pk: number; body: Record<string, unknown> }) =>
      api.put(`/sys/depts/${pk}`, body),
    onSuccess: () => {
      toast.success('部门更新成功')
      qc.invalidateQueries({ queryKey: ['admin-depts'] })
      setEditDept(null)
      setFormOpen(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (pk: number) => api.delete(`/sys/depts/${pk}`),
    onSuccess: () => {
      toast.success('部门已删除')
      qc.invalidateQueries({ queryKey: ['admin-depts'] })
      setDeleteDept(null)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  function openCreate(pid: number | null = null) {
    setEditDept(null)
    setParentId(pid)
    setFormOpen(true)
  }

  function openEdit(dept: DeptNode) {
    setEditDept(dept)
    setParentId(dept.parent_id)
    setFormOpen(true)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">部门管理</h1>
        <Button onClick={() => openCreate()}>创建部门</Button>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="搜索部门名..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
      </div>

      <div className="rounded-md border">
        {isLoading ? (
          <div className="text-center py-8 text-muted-foreground">加载中...</div>
        ) : !deptTree?.length ? (
          <div className="text-center py-8 text-muted-foreground">暂无数据</div>
        ) : (
          <div className="divide-y">
            {deptTree.map((node) => (
              <DeptTreeRow
                key={node.id}
                node={node}
                depth={0}
                onEdit={openEdit}
                onDelete={setDeleteDept}
                onAddChild={(pid) => openCreate(pid)}
              />
            ))}
          </div>
        )}
      </div>

      <DeptFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        dept={editDept}
        parentId={parentId}
        depts={flatDepts}
        onSubmit={(body) =>
          editDept
            ? updateMutation.mutate({ pk: editDept.id, body })
            : createMutation.mutate(body)
        }
        loading={createMutation.isPending || updateMutation.isPending}
      />

      <AlertDialog open={!!deleteDept} onOpenChange={(open) => !open && setDeleteDept(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除部门 <strong>{deleteDept?.name}</strong> 吗？
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteDept && deleteMutation.mutate(deleteDept.id)}>
              删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function DeptTreeRow({
  node,
  depth,
  onEdit,
  onDelete,
  onAddChild,
}: {
  node: DeptNode
  depth: number
  onEdit: (dept: DeptNode) => void
  onDelete: (dept: DeptNode) => void
  onAddChild: (pid: number) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = !!node.children?.length

  return (
    <>
      <div
        className="flex items-center gap-2 px-4 py-2 hover:bg-accent/30"
        style={{ paddingLeft: `${depth * 24 + 16}px` }}
      >
        <button
          type="button"
          className="w-5 h-5 flex items-center justify-center text-muted-foreground"
          onClick={() => setExpanded(!expanded)}
        >
          {hasChildren ? (expanded ? '▾' : '▸') : '·'}
        </button>
        <span className="font-medium text-sm flex-1">{node.name}</span>
        {node.leader && (
          <span className="text-xs text-muted-foreground">负责人: {node.leader}</span>
        )}
        <Badge variant={node.status === 1 ? 'default' : 'destructive'} className="text-xs">
          {node.status === 1 ? '启用' : '禁用'}
        </Badge>
        <div className="flex gap-1 ml-2">
          <Button variant="ghost" size="sm" onClick={() => onAddChild(node.id)}>
            添加子部门
          </Button>
          <Button variant="ghost" size="sm" onClick={() => onEdit(node)}>
            编辑
          </Button>
          <Button variant="ghost" size="sm" className="text-destructive" onClick={() => onDelete(node)}>
            删除
          </Button>
        </div>
      </div>
      {expanded &&
        node.children?.map((child) => (
          <DeptTreeRow
            key={child.id}
            node={child}
            depth={depth + 1}
            onEdit={onEdit}
            onDelete={onDelete}
            onAddChild={onAddChild}
          />
        ))}
    </>
  )
}

function DeptFormDialog({
  open,
  onOpenChange,
  dept,
  parentId,
  depts,
  onSubmit,
  loading,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  dept: DeptNode | null
  parentId: number | null
  depts: { id: number; name: string; depth: number }[]
  onSubmit: (body: Record<string, unknown>) => void
  loading: boolean
}) {
  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const pid = fd.get('parent_id') as string
    onSubmit({
      name: fd.get('name'),
      parent_id: pid && pid !== '0' ? Number(pid) : null,
      sort: Number(fd.get('sort') || 0),
      leader: fd.get('leader') || undefined,
      phone: fd.get('phone') || undefined,
      email: fd.get('email') || undefined,
      status: Number(fd.get('status')),
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{dept ? '编辑部门' : '创建部门'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>部门名称 *</Label>
              <Input name="name" required defaultValue={dept?.name ?? ''} />
            </div>
            <div className="space-y-2">
              <Label>上级部门</Label>
              <Select name="parent_id" defaultValue={String(parentId ?? dept?.parent_id ?? 0)}>
                <SelectTrigger>
                  <SelectValue placeholder="无" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">无（顶级部门）</SelectItem>
                  {depts.map((d) => (
                    <SelectItem key={d.id} value={String(d.id)}>
                      {'　'.repeat(d.depth)}{d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>负责人</Label>
              <Input name="leader" defaultValue={dept?.leader ?? ''} />
            </div>
            <div className="space-y-2">
              <Label>排序</Label>
              <Input name="sort" type="number" defaultValue={dept?.sort ?? 0} />
            </div>
            <div className="space-y-2">
              <Label>联系电话</Label>
              <Input name="phone" defaultValue={dept?.phone ?? ''} />
            </div>
            <div className="space-y-2">
              <Label>邮箱</Label>
              <Input name="email" type="email" defaultValue={dept?.email ?? ''} />
            </div>
            <div className="space-y-2">
              <Label>状态</Label>
              <select
                name="status"
                defaultValue={dept?.status ?? 1}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              >
                <option value={1}>启用</option>
                <option value={0}>禁用</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={loading}>
              {loading ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function flattenTree(
  nodes: DeptNode[],
  depth = 0,
): { id: number; name: string; depth: number }[] {
  const result: { id: number; name: string; depth: number }[] = []
  for (const node of nodes) {
    result.push({ id: node.id, name: node.name, depth })
    if (node.children?.length) {
      result.push(...flattenTree(node.children, depth + 1))
    }
  }
  return result
}
