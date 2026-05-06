'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'

interface OnlineUser {
  id: number
  session_uuid: string
  username: string
  nickname: string
  ip: string
  os: string
  browser: string
  device: string
  status: number
  last_login_time: string
  expire_time: string
}

export default function OnlineMonitorPage() {
  const api = useApi()
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [kickTarget, setKickTarget] = useState<OnlineUser | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-online', search],
    queryFn: () =>
      api.get<OnlineUser[]>(`/monitors/sessions${search ? `?username=${search}` : ''}`),
  })

  const kickMutation = useMutation({
    mutationFn: (user: OnlineUser) =>
      api.delete(`/monitors/sessions/${user.id}`, { session_uuid: user.session_uuid }),
    onSuccess: () => {
      toast.success('用户已踢出')
      qc.invalidateQueries({ queryKey: ['admin-online'] })
      setKickTarget(null)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">在线用户</h1>
          {data && (
            <span className="text-sm text-muted-foreground">当前在线: {data.length}</span>
          )}
        </div>
      </div>

      <Input
        placeholder="搜索用户名..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-xs"
      />

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>用户名</TableHead>
              <TableHead>昵称</TableHead>
              <TableHead>IP</TableHead>
              <TableHead>浏览器</TableHead>
              <TableHead>操作系统</TableHead>
              <TableHead>设备</TableHead>
              <TableHead>登录时间</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">加载中...</TableCell>
              </TableRow>
            ) : !data?.length ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">暂无在线用户</TableCell>
              </TableRow>
            ) : (
              data.map((u) => (
                <TableRow key={u.session_uuid}>
                  <TableCell className="font-medium">{u.username}</TableCell>
                  <TableCell>{u.nickname}</TableCell>
                  <TableCell className="text-xs">{u.ip}</TableCell>
                  <TableCell className="text-xs">{u.browser}</TableCell>
                  <TableCell className="text-xs">{u.os}</TableCell>
                  <TableCell className="text-xs">{u.device}</TableCell>
                  <TableCell className="text-xs">{new Date(u.last_login_time).toLocaleString('zh-CN')}</TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" className="text-destructive" onClick={() => setKickTarget(u)}>
                      踢出
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <AlertDialog open={!!kickTarget} onOpenChange={(open) => !open && setKickTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认踢出</AlertDialogTitle>
            <AlertDialogDescription>
              确定要踢出用户 <strong>{kickTarget?.nickname}</strong>（{kickTarget?.username}）吗？
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => kickTarget && kickMutation.mutate(kickTarget)}>踢出</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
