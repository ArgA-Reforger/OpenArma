'use client'

import { useState, useEffect } from 'react'
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

const MENU_TYPES = ['目录', '菜单', '按钮', '内嵌', '链接'] as const
const MENU_TYPE_VARIANTS: Record<number, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  0: 'default',
  1: 'secondary',
  2: 'outline',
  3: 'secondary',
  4: 'secondary',
}

interface MenuNode {
  id: number
  title: string
  name: string
  path: string | null
  parent_id: number | null
  sort: number
  icon: string | null
  type: number
  component: string | null
  perms: string | null
  status: number
  display: number
  cache: number
  link: string | null
  remark: string | null
  children?: MenuNode[]
  created_time: string
}

export default function MenusPage() {
  const api = useApi()
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editMenu, setEditMenu] = useState<MenuNode | null>(null)
  const [deleteMenu, setDeleteMenu] = useState<MenuNode | null>(null)
  const [parentId, setParentId] = useState<number | null>(null)

  const { data: menuTree, isLoading } = useQuery({
    queryKey: ['admin-menus', search],
    queryFn: () =>
      api.get<MenuNode[]>(`/sys/menus${search ? `?title=${search}` : ''}`),
  })

  const flatMenus = flattenTree(menuTree ?? [])

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/sys/menus', body),
    onSuccess: () => {
      toast.success('菜单创建成功')
      qc.invalidateQueries({ queryKey: ['admin-menus'] })
      setFormOpen(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ pk, body }: { pk: number; body: Record<string, unknown> }) =>
      api.put(`/sys/menus/${pk}`, body),
    onSuccess: () => {
      toast.success('菜单更新成功')
      qc.invalidateQueries({ queryKey: ['admin-menus'] })
      setEditMenu(null)
      setFormOpen(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (pk: number) => api.delete(`/sys/menus/${pk}`),
    onSuccess: () => {
      toast.success('菜单已删除')
      qc.invalidateQueries({ queryKey: ['admin-menus'] })
      setDeleteMenu(null)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  function openCreate(pid: number | null = null) {
    setEditMenu(null)
    setParentId(pid)
    setFormOpen(true)
  }

  function openEdit(menu: MenuNode) {
    setEditMenu(menu)
    setParentId(menu.parent_id)
    setFormOpen(true)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">菜单管理</h1>
        <Button onClick={() => openCreate()}>创建菜单</Button>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="搜索菜单标题..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
      </div>

      <div className="rounded-md border">
        {isLoading ? (
          <div className="text-center py-8 text-muted-foreground">加载中...</div>
        ) : !menuTree?.length ? (
          <div className="text-center py-8 text-muted-foreground">暂无数据</div>
        ) : (
          <div className="divide-y">
            {menuTree.map((node) => (
              <MenuTreeRow
                key={node.id}
                node={node}
                depth={0}
                onEdit={openEdit}
                onDelete={setDeleteMenu}
                onAddChild={(pid) => openCreate(pid)}
              />
            ))}
          </div>
        )}
      </div>

      <MenuFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        menu={editMenu}
        parentId={parentId}
        menus={flatMenus}
        onSubmit={(body) =>
          editMenu
            ? updateMutation.mutate({ pk: editMenu.id, body })
            : createMutation.mutate(body)
        }
        loading={createMutation.isPending || updateMutation.isPending}
      />

      <AlertDialog open={!!deleteMenu} onOpenChange={(open) => !open && setDeleteMenu(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除菜单 <strong>{deleteMenu?.title}</strong> 吗？
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteMenu && deleteMutation.mutate(deleteMenu.id)}>
              删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function MenuTreeRow({
  node,
  depth,
  onEdit,
  onDelete,
  onAddChild,
}: {
  node: MenuNode
  depth: number
  onEdit: (menu: MenuNode) => void
  onDelete: (menu: MenuNode) => void
  onAddChild: (pid: number) => void
}) {
  const [expanded, setExpanded] = useState(depth < 2)
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
        <span className="font-medium text-sm">{node.title}</span>
        <Badge variant={MENU_TYPE_VARIANTS[node.type] ?? 'outline'} className="text-xs">
          {MENU_TYPES[node.type] ?? node.type}
        </Badge>
        {node.perms && (
          <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{node.perms}</code>
        )}
        <span className="flex-1" />
        {node.path && (
          <span className="text-xs text-muted-foreground">{node.path}</span>
        )}
        <Badge variant={node.status === 1 ? 'default' : 'destructive'} className="text-xs">
          {node.status === 1 ? '启用' : '禁用'}
        </Badge>
        <div className="flex gap-1 ml-2">
          {node.type === 0 && (
            <Button variant="ghost" size="sm" onClick={() => onAddChild(node.id)}>
              添加子项
            </Button>
          )}
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
          <MenuTreeRow
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

function MenuFormDialog({
  open,
  onOpenChange,
  menu,
  parentId,
  menus,
  onSubmit,
  loading,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  menu: MenuNode | null
  parentId: number | null
  menus: { id: number; title: string; depth: number }[]
  onSubmit: (body: Record<string, unknown>) => void
  loading: boolean
}) {
  const [menuType, setMenuType] = useState(menu?.type ?? 0)

  useEffect(() => {
    if (open) setMenuType(menu?.type ?? 0)
  }, [open, menu])

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const pid = fd.get('parent_id') as string
    onSubmit({
      title: fd.get('title'),
      name: fd.get('name'),
      path: fd.get('path') || undefined,
      parent_id: pid && pid !== '0' ? Number(pid) : undefined,
      sort: Number(fd.get('sort') || 0),
      icon: fd.get('icon') || undefined,
      type: menuType,
      component: fd.get('component') || undefined,
      perms: fd.get('perms') || undefined,
      status: Number(fd.get('status')),
      display: Number(fd.get('display')),
      cache: Number(fd.get('cache')),
      link: fd.get('link') || undefined,
      remark: fd.get('remark') || undefined,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{menu ? '编辑菜单' : '创建菜单'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>标题 *</Label>
              <Input name="title" required defaultValue={menu?.title ?? ''} />
            </div>
            <div className="space-y-2">
              <Label>名称 *</Label>
              <Input name="name" required defaultValue={menu?.name ?? ''} />
            </div>
            <div className="space-y-2">
              <Label>类型 *</Label>
              <Select
                value={String(menuType)}
                onValueChange={(v) => setMenuType(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MENU_TYPES.map((label, i) => (
                    <SelectItem key={i} value={String(i)}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>上级菜单</Label>
              <Select name="parent_id" defaultValue={String(parentId ?? menu?.parent_id ?? 0)}>
                <SelectTrigger>
                  <SelectValue placeholder="无" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">无（顶级）</SelectItem>
                  {menus.map((m) => (
                    <SelectItem key={m.id} value={String(m.id)}>
                      {'　'.repeat(m.depth)}{m.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {(menuType === 1 || menuType === 3) && (
              <>
                <div className="space-y-2">
                  <Label>路径</Label>
                  <Input name="path" defaultValue={menu?.path ?? ''} />
                </div>
                <div className="space-y-2">
                  <Label>组件</Label>
                  <Input name="component" defaultValue={menu?.component ?? ''} />
                </div>
              </>
            )}
            {menuType === 2 && (
              <div className="space-y-2 col-span-2">
                <Label>权限标识</Label>
                <Input name="perms" defaultValue={menu?.perms ?? ''} placeholder="sys:user:add" />
              </div>
            )}
            {menuType === 4 && (
              <div className="space-y-2 col-span-2">
                <Label>链接地址</Label>
                <Input name="link" defaultValue={menu?.link ?? ''} />
              </div>
            )}
            <div className="space-y-2">
              <Label>图标</Label>
              <Input name="icon" defaultValue={menu?.icon ?? ''} />
            </div>
            <div className="space-y-2">
              <Label>排序</Label>
              <Input name="sort" type="number" defaultValue={menu?.sort ?? 0} />
            </div>
            <div className="space-y-2">
              <Label>状态</Label>
              <select
                name="status"
                defaultValue={menu?.status ?? 1}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              >
                <option value={1}>启用</option>
                <option value={0}>禁用</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>显示</Label>
              <select
                name="display"
                defaultValue={menu?.display ?? 1}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              >
                <option value={1}>显示</option>
                <option value={0}>隐藏</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>缓存</Label>
              <select
                name="cache"
                defaultValue={menu?.cache ?? 1}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              >
                <option value={1}>是</option>
                <option value={0}>否</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>备注</Label>
              <Input name="remark" defaultValue={menu?.remark ?? ''} />
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
  nodes: MenuNode[],
  depth = 0,
): { id: number; title: string; depth: number }[] {
  const result: { id: number; title: string; depth: number }[] = []
  for (const node of nodes) {
    result.push({ id: node.id, title: node.title, depth })
    if (node.children?.length) {
      result.push(...flattenTree(node.children, depth + 1))
    }
  }
  return result
}
