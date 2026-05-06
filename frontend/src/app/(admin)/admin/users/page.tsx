'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
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
      toast.success('用户创建成功')
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
      toast.success('密码重置成功')
      setResetPwdUser(null)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (pk: number) => api.delete(`/sys/users/${pk}`),
    onSuccess: () => {
      toast.success('用户已删除')
      qc.invalidateQueries({ queryKey: ['admin-users'] })
      setDeleteUser(null)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">用户管理</h1>
        <Button onClick={() => setCreateOpen(true)}>创建用户</Button>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="搜索用户名..."
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
              <TableHead>用户名</TableHead>
              <TableHead>昵称</TableHead>
              <TableHead>部门</TableHead>
              <TableHead>角色</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>权限</TableHead>
              <TableHead>最后登录</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  加载中...
                </TableCell>
              </TableRow>
            ) : !data?.items?.length ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  暂无数据
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
                      {u.status === 1 ? '启用' : '禁用'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {u.is_superuser && (
                        <Badge variant="default" className="text-xs">
                          超管
                        </Badge>
                      )}
                      {u.is_staff && (
                        <Badge variant="outline" className="text-xs">
                          管理
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {u.last_login_time ? new Date(u.last_login_time).toLocaleString('zh-CN') : '-'}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setResetPwdUser(u)}
                      >
                        重置密码
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => setDeleteUser(u)}
                      >
                        删除
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
            共 {data.total} 条，第 {data.page}/{data.total_pages} 页
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              上一页
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              下一页
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
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除用户 <strong>{deleteUser?.username}</strong> 吗？此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteUser && deleteMutation.mutate(deleteUser.id)}
            >
              删除
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
          <DialogTitle>创建用户</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>用户名 *</Label>
              <Input name="username" required />
            </div>
            <div className="space-y-2">
              <Label>密码 *</Label>
              <Input name="password" type="password" required />
            </div>
            <div className="space-y-2">
              <Label>昵称</Label>
              <Input name="nickname" />
            </div>
            <div className="space-y-2">
              <Label>邮箱</Label>
              <Input name="email" type="email" />
            </div>
            <div className="space-y-2">
              <Label>部门 *</Label>
              <Select name="dept_id" required>
                <SelectTrigger>
                  <SelectValue placeholder="选择部门" />
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
              <Label>角色</Label>
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
              {loading ? '创建中...' : '创建'}
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
  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    onSubmit(fd.get('password') as string)
  }

  return (
    <Dialog open={!!user} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>重置密码 - {user?.username}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>新密码</Label>
            <Input name="password" type="password" required minLength={6} />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={loading}>
              {loading ? '重置中...' : '确认重置'}
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
