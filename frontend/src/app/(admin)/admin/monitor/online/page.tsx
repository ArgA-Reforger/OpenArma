'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
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
  const { t, locale } = useI18n()
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
      toast.success(t('monitor.kickSuccess'))
      qc.invalidateQueries({ queryKey: ['admin-online'] })
      setKickTarget(null)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">{t('monitor.online')}</h1>
          {data && (
            <span className="text-sm text-muted-foreground">{t('monitor.currentOnline', { count: data.length })}</span>
          )}
        </div>
      </div>

      <Input
        placeholder={t('log.searchUsername')}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-xs"
      />

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('user.username')}</TableHead>
              <TableHead>{t('user.nickname')}</TableHead>
              <TableHead>{t('log.ip')}</TableHead>
              <TableHead>{t('log.browser')}</TableHead>
              <TableHead>{t('log.os')}</TableHead>
              <TableHead>{t('log.device')}</TableHead>
              <TableHead>{t('log.loginTime')}</TableHead>
              <TableHead className="text-right">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">{t('common.loading')}</TableCell>
              </TableRow>
            ) : !data?.length ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">{t('monitor.noOnlineUsers')}</TableCell>
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
                  <TableCell className="text-xs">{new Date(u.last_login_time).toLocaleString(locale)}</TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" className="text-destructive" onClick={() => setKickTarget(u)}>
                      {t('monitor.kick')}
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
            <AlertDialogTitle>{t('monitor.confirmKickTitle')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('monitor.confirmKick', { name: kickTarget?.nickname ?? '', username: kickTarget?.username ?? '' })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={() => kickTarget && kickMutation.mutate(kickTarget)}>{t('monitor.kick')}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
