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

interface Dept {
  id: number
  name: string
}

interface Role {
  id: number
  name: string
}

interface UserItem {
  id: number
  uuid: string
  username: string
  nickname: string
  email: string | null
  phone: string | null
  status: number
  is_superuser: boolean
  is_staff: boolean
  is_multi_login: boolean
  dept: Dept | null
  roles: Role[]
  join_time: string
  last_login_time: string | null
}

interface PageData<T> {
  items: T[]
  total: number
  page: number
  size: number
  total_pages: number
}

export default function UsersPage() {
  const api = useApi()
  const qc = useQueryClient()
  const { t, locale } = useI18n()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [resetPwdUser, setResetPwdUser] = useState<UserItem | null>(null)
  const [deleteUser, setDeleteUser] = useState<UserItem | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users', page, search],
    queryFn: () =>
      api.get<PageData<UserItem>>(
        `/sys/users?page=${page}&size=20${search ? `&username=${search}` : ''}`,
      ),
  })

  const { data: allRoles } = useQuery({
    queryKey: ['admin-roles-all'],
    queryFn: () => api.get<Role[]>('/sys/roles/all'),
  })

  const { data: deptTree } = useQuery({
    queryKey: ['admin-depts-tree'],
    queryFn: () => api.get<Dept[]>('/sys/depts'),
  })

  const flatDepts = flattenTree(deptTree ?? [])

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/sys/users', body),
    onSuccess: () => {
      toast.success(t('user.userCreated'))
      qc.invalidateQueries({ queryKey: ['admin-users'] })
      setCreateOpen(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ pk, type }: { pk: number; type: string }) =>
      api.put(`/sys/users/${pk}/permissions?type=${type}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-users'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const resetPwdMutation = useMutation({
    mutationFn: ({ pk, password }: { pk: number; password: string }) =>
      api.put(`/sys/users/${pk}/password`, { password }),
    onSuccess: () => {
      toast.success(t('user.passwordResetSuccess'))
      setResetPwdUser(null)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (pk: number) => api.delete(`/sys/users/${pk}`),
    onSuccess: () => {
      toast.success(t('user.userDeleted'))
      qc.invalidateQueries({ queryKey: ['admin-users'] })
      setDeleteUser(null)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('user.title')}</h1>
        <Button onClick={() => setCreateOpen(true)}>{t('user.createUser')}</Button>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder={t('user.searchUsername')}
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
              <TableHead>{t('user.username')}</TableHead>
              <TableHead>{t('user.nickname')}</TableHead>
              <TableHead>{t('user.dept')}</TableHead>
              <TableHead>{t('user.roles')}</TableHead>
              <TableHead>{t('common.status')}</TableHead>
              <TableHead>{t('menu.perms')}</TableHead>
              <TableHead>{t('user.lastLogin')}</TableHead>
              <TableHead className="text-right">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  {t('common.loading')}
                </TableCell>
              </TableRow>
            ) : !data?.items?.length ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  {t('common.noData')}
                </TableCell>
              </TableRow>
            ) : (
              data.items.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="font-medium">{u.username}</TableCell>
                  <TableCell>{u.nickname}</TableCell>
                  <TableCell>{u.dept?.name ?? '-'}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {u.roles.map((r) => (
                        <Badge key={r.id} variant="secondary" className="text-xs">
                          {r.name}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={u.status === 1 ? 'default' : 'destructive'}
                      className="cursor-pointer"
                      onClick={() => toggleMutation.mutate({ pk: u.id, type: 'status' })}
                    >
                      {u.status === 1 ? t('common.enabled') : t('common.disabled')}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {u.is_superuser && (
                        <Badge variant="default" className="text-xs">
                          {t('user.superAdmin')}
                        </Badge>
                      )}
                      {u.is_staff && (
                        <Badge variant="outline" className="text-xs">
                          {t('user.admin')}
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {u.last_login_time ? new Date(u.last_login_time).toLocaleString(locale) : '-'}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setResetPwdUser(u)}
                      >
                        {t('user.resetPassword')}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => setDeleteUser(u)}
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
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              {t('common.prevPage')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              {t('common.nextPage')}
            </Button>
          </div>
        </div>
      )}

      <CreateUserDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onSubmit={(body) => createMutation.mutate(body)}
        loading={createMutation.isPending}
        roles={allRoles ?? []}
        depts={flatDepts}
      />

      <ResetPasswordDialog
        user={resetPwdUser}
        onClose={() => setResetPwdUser(null)}
        onSubmit={(password) =>
          resetPwdUser && resetPwdMutation.mutate({ pk: resetPwdUser.id, password })
        }
        loading={resetPwdMutation.isPending}
      />

      <AlertDialog open={!!deleteUser} onOpenChange={(open) => !open && setDeleteUser(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('common.confirmDelete')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('user.confirmDelete', { name: deleteUser?.username ?? '' })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteUser && deleteMutation.mutate(deleteUser.id)}
            >
              {t('common.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function CreateUserDialog({
  open,
  onOpenChange,
  onSubmit,
  loading,
  roles,
  depts,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (body: Record<string, unknown>) => void
  loading: boolean
  roles: Role[]
  depts: { id: number; name: string; depth: number }[]
}) {
  const { t } = useI18n()
  const [selectedRoles, setSelectedRoles] = useState<number[]>([])

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    onSubmit({
      username: fd.get('username'),
      password: fd.get('password'),
      nickname: fd.get('nickname') || undefined,
      email: fd.get('email') || undefined,
      dept_id: Number(fd.get('dept_id')),
      roles: selectedRoles,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('user.createUser')}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{t('user.username')} *</Label>
              <Input name="username" required />
            </div>
            <div className="space-y-2">
              <Label>{t('user.password')} *</Label>
              <Input name="password" type="password" required />
            </div>
            <div className="space-y-2">
              <Label>{t('user.nickname')}</Label>
              <Input name="nickname" />
            </div>
            <div className="space-y-2">
              <Label>{t('user.email')}</Label>
              <Input name="email" type="email" />
            </div>
            <div className="space-y-2">
              <Label>{t('user.dept')} *</Label>
              <Select name="dept_id" required>
                <SelectTrigger>
                  <SelectValue placeholder={t('user.selectDept')} />
                </SelectTrigger>
                <SelectContent>
                  {depts.map((d) => (
                    <SelectItem key={d.id} value={String(d.id)}>
                      {'　'.repeat(d.depth)}{d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>{t('user.roles')}</Label>
              <div className="flex flex-wrap gap-2 rounded-md border p-2 min-h-9">
                {roles.map((r) => (
                  <Badge
                    key={r.id}
                    variant={selectedRoles.includes(r.id) ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() =>
                      setSelectedRoles((prev) =>
                        prev.includes(r.id) ? prev.filter((id) => id !== r.id) : [...prev, r.id],
                      )
                    }
                  >
                    {r.name}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={loading}>
              {loading ? t('user.creating') : t('common.create')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function ResetPasswordDialog({
  user,
  onClose,
  onSubmit,
  loading,
}: {
  user: UserItem | null
  onClose: () => void
  onSubmit: (password: string) => void
  loading: boolean
}) {
  const { t } = useI18n()

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    onSubmit(fd.get('password') as string)
  }

  return (
    <Dialog open={!!user} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('user.resetPasswordFor', { name: user?.username ?? '' })}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>{t('user.newPassword')}</Label>
            <Input name="password" type="password" required minLength={6} />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={loading}>
              {loading ? t('user.resetting') : t('user.confirmReset')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

interface TreeNode {
  id: number
  name: string
  children?: TreeNode[]
}

function flattenTree(
  nodes: TreeNode[],
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
