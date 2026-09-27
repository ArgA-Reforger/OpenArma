'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
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

interface RoleItem {
  id: number
  name: string
  status: number
  is_filter_scopes: boolean
  remark: string | null
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

interface MenuTreeNode {
  id: number
  title: string
  type: number
  children?: MenuTreeNode[]
}

export default function RolesPage() {
  const api = useApi()
  const qc = useQueryClient()
  const { t, locale } = useI18n()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editRole, setEditRole] = useState<RoleItem | null>(null)
  const [menuRole, setMenuRole] = useState<RoleItem | null>(null)
  const [deleteIds, setDeleteIds] = useState<number[]>([])

  const { data, isLoading } = useQuery({
    queryKey: ['admin-roles', page, search],
    queryFn: () =>
      api.get<PageData<RoleItem>>(
        `/sys/roles?page=${page}&size=20${search ? `&name=${search}` : ''}`,
      ),
  })

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/sys/roles', body),
    onSuccess: () => {
      toast.success(t('role.roleCreated'))
      qc.invalidateQueries({ queryKey: ['admin-roles'] })
      setFormOpen(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ pk, body }: { pk: number; body: Record<string, unknown> }) =>
      api.put(`/sys/roles/${pk}`, body),
    onSuccess: () => {
      toast.success(t('role.roleUpdated'))
      qc.invalidateQueries({ queryKey: ['admin-roles'] })
      setEditRole(null)
      setFormOpen(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (pks: number[]) => api.delete('/sys/roles', { pks }),
    onSuccess: () => {
      toast.success(t('role.roleDeleted'))
      qc.invalidateQueries({ queryKey: ['admin-roles'] })
      setDeleteIds([])
    },
    onError: (e: Error) => toast.error(e.message),
  })

  function openCreate() {
    setEditRole(null)
    setFormOpen(true)
  }

  function openEdit(role: RoleItem) {
    setEditRole(role)
    setFormOpen(true)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('role.title')}</h1>
        <Button onClick={openCreate}>{t('role.createRole')}</Button>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder={t('role.searchRole')}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          className="max-w-xs"
        />
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('role.roleName')}</TableHead>
              <TableHead>{t('common.status')}</TableHead>
              <TableHead>{t('role.dataFilter')}</TableHead>
              <TableHead>{t('common.remark')}</TableHead>
              <TableHead>{t('common.createdTime')}</TableHead>
              <TableHead className="text-right">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                  {t('common.loading')}
                </TableCell>
              </TableRow>
            ) : !data?.items?.length ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                  {t('common.noData')}
                </TableCell>
              </TableRow>
            ) : (
              data.items.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell>
                    <Badge variant={r.status === 1 ? 'default' : 'destructive'}>
                      {r.status === 1 ? t('common.enabled') : t('common.disabled')}
                    </Badge>
                  </TableCell>
                  <TableCell>{r.is_filter_scopes ? t('common.yes') : t('common.no')}</TableCell>
                  <TableCell className="text-muted-foreground">{r.remark ?? '-'}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {new Date(r.created_time).toLocaleString(locale)}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(r)}>
                        {t('common.edit')}
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setMenuRole(r)}>
                        {t('role.menuPermission')}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => setDeleteIds([r.id])}
                      >
                        {t('common.delete')}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            {t('common.total', { total: data.total })}, {t('common.pageInfo', { page: data.page, totalPages: data.total_pages })}
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              {t('common.prevPage')}
            </Button>
            <Button variant="outline" size="sm" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)}>
              {t('common.nextPage')}
            </Button>
          </div>
        </div>
      )}

      <RoleFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        role={editRole}
        onSubmit={(body) =>
          editRole
            ? updateMutation.mutate({ pk: editRole.id, body })
            : createMutation.mutate(body)
        }
        loading={createMutation.isPending || updateMutation.isPending}
      />

      {menuRole && (
        <MenuPermissionDialog
          role={menuRole}
          onClose={() => setMenuRole(null)}
        />
      )}

      <AlertDialog open={deleteIds.length > 0} onOpenChange={(open) => !open && setDeleteIds([])}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('common.confirmDelete')}</AlertDialogTitle>
            <AlertDialogDescription>{t('role.confirmBatchDelete', { count: deleteIds.length })}</AlertDialogDescription>
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

function RoleFormDialog({
  open,
  onOpenChange,
  role,
  onSubmit,
  loading,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  role: RoleItem | null
  onSubmit: (body: Record<string, unknown>) => void
  loading: boolean
}) {
  const { t } = useI18n()

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    onSubmit({
      name: fd.get('name'),
      status: Number(fd.get('status')),
      remark: fd.get('remark') || undefined,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{role ? t('role.editRole') : t('role.createRole')}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>{t('role.roleName')} *</Label>
            <Input name="name" required defaultValue={role?.name ?? ''} />
          </div>
          <div className="space-y-2">
            <Label>{t('common.status')}</Label>
            <select
              name="status"
              defaultValue={role?.status ?? 1}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
            >
              <option value={1}>{t('common.enabled')}</option>
              <option value={0}>{t('common.disabled')}</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label>{t('common.remark')}</Label>
            <Input name="remark" defaultValue={role?.remark ?? ''} />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={loading}>
              {loading ? t('common.saving') : t('common.save')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function MenuPermissionDialog({
  role,
  onClose,
}: {
  role: RoleItem
  onClose: () => void
}) {
  const api = useApi()
  const qc = useQueryClient()
  const { t } = useI18n()
  const [checkedIds, setCheckedIds] = useState<Set<number>>(new Set())
  const [initialized, setInitialized] = useState(false)

  const { data: menuTree } = useQuery({
    queryKey: ['admin-menus-tree'],
    queryFn: () => api.get<MenuTreeNode[]>('/sys/menus'),
  })

  const { data: roleMenus } = useQuery({
    queryKey: ['admin-role-menus', role.id],
    queryFn: () => api.get<MenuTreeNode[]>(`/sys/roles/${role.id}/menus`),
  })

  if (roleMenus && !initialized) {
    const ids = new Set<number>()
    collectLeafIds(roleMenus, ids)
    setCheckedIds(ids)
    setInitialized(true)
  }

  const saveMutation = useMutation({
    mutationFn: (menus: number[]) =>
      api.put(`/sys/roles/${role.id}/menus`, { menus }),
    onSuccess: () => {
      toast.success(t('role.permissionUpdated'))
      qc.invalidateQueries({ queryKey: ['admin-role-menus', role.id] })
      onClose()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  function toggleNode(id: number, allDescendants: number[]) {
    setCheckedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
        allDescendants.forEach((d) => next.delete(d))
      } else {
        next.add(id)
        allDescendants.forEach((d) => next.add(d))
      }
      return next
    })
  }

  function handleSave() {
    saveMutation.mutate(Array.from(checkedIds))
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{t('role.menuPermissionFor', { name: role.name })}</DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto py-2">
          {menuTree?.map((node) => (
            <MenuTreeItem
              key={node.id}
              node={node}
              checkedIds={checkedIds}
              onToggle={toggleNode}
              depth={0}
            />
          ))}
        </div>
        <DialogFooter>
          <Button onClick={handleSave} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? t('common.saving') : t('common.save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function MenuTreeItem({
  node,
  checkedIds,
  onToggle,
  depth,
}: {
  node: MenuTreeNode
  checkedIds: Set<number>
  onToggle: (id: number, descendants: number[]) => void
  depth: number
}) {
  const { t } = useI18n()
  const descendants = getAllIds(node.children ?? [])
  const checked = checkedIds.has(node.id)
  const menuTypes = [t('menu.typeDirectory'), t('menu.typeMenu'), t('menu.typeButton'), t('menu.typeEmbed'), t('menu.typeLink')]

  return (
    <div>
      <div
        className="flex items-center gap-2 py-1 hover:bg-accent/50 rounded px-2"
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
      >
        <Checkbox
          checked={checked}
          onCheckedChange={() => onToggle(node.id, descendants)}
        />
        <span className="text-sm">{node.title}</span>
        <Badge variant="outline" className="text-xs ml-auto">
          {menuTypes[node.type] ?? node.type}
        </Badge>
      </div>
      {node.children?.map((child) => (
        <MenuTreeItem
          key={child.id}
          node={child}
          checkedIds={checkedIds}
          onToggle={onToggle}
          depth={depth + 1}
        />
      ))}
    </div>
  )
}

function getAllIds(nodes: MenuTreeNode[]): number[] {
  const ids: number[] = []
  for (const n of nodes) {
    ids.push(n.id)
    if (n.children) ids.push(...getAllIds(n.children))
  }
  return ids
}

function collectLeafIds(nodes: MenuTreeNode[], ids: Set<number>) {
  for (const n of nodes) {
    if (!n.children?.length) {
      ids.add(n.id)
    } else {
      collectLeafIds(n.children, ids)
    }
  }
}
