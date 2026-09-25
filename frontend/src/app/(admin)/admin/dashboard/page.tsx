'use client'

import { useQuery } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface ServerInfo {
  cpu: { usage: number; logical_num: number }
  mem: { total: string; used: string; usage: number }
  service: { name: string; version: string; uptime: string }
}

export default function AdminDashboard() {
  const api = useApi()
  const { t } = useI18n()

  const { data: server } = useQuery({
    queryKey: ['admin-dashboard-server'],
    queryFn: () => api.get<ServerInfo>('/monitors/server'),
    refetchInterval: 30000,
  })

  const { data: online } = useQuery({
    queryKey: ['admin-dashboard-online'],
    queryFn: () => api.get<unknown[]>('/monitors/sessions'),
    refetchInterval: 30000,
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('dashboard.title')}</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title={t('dashboard.cpuUsage')}
          value={server ? `${server.cpu.usage}%` : '-'}
          sub={server ? t('dashboard.cores', { count: server.cpu.logical_num }) : ''}
        />
        <StatCard
          title={t('dashboard.memUsage')}
          value={server ? `${server.mem.usage}%` : '-'}
          sub={server ? `${server.mem.used} / ${server.mem.total}` : ''}
        />
        <StatCard
          title={t('dashboard.onlineUsers')}
          value={online ? String(online.length) : '-'}
          sub={t('dashboard.activeSessions')}
        />
        <StatCard
          title={t('dashboard.uptime')}
          value={server?.service.uptime ?? '-'}
          sub={server ? `${server.service.name} ${server.service.version}` : ''}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>{t('dashboard.quickNav')}</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2">
              {[
                { href: '/admin/users', label: t('user.title') },
                { href: '/admin/roles', label: t('role.title') },
                { href: '/admin/logs/login', label: t('log.loginLog') },
                { href: '/admin/logs/opera', label: t('log.operaLog') },
                { href: '/admin/monitor/online', label: t('monitor.online') },
                { href: '/admin/monitor/server', label: t('monitor.server') },
                { href: '/admin/monitor/redis', label: t('monitor.redis') },
                { href: '/admin/config', label: t('config.title') },
              ].map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="block rounded-md border p-3 text-sm hover:bg-accent transition-colors"
                >
                  {item.label}
                </a>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>{t('dashboard.systemInfo')}</CardTitle></CardHeader>
          <CardContent>
            {server ? (
              <dl className="space-y-2">
                <InfoRow label={t('dashboard.serviceName')} value={server.service.name} />
                <InfoRow label={t('dashboard.version')} value={server.service.version} />
                <InfoRow label={t('dashboard.uptime')} value={server.service.uptime} />
                <InfoRow label={t('dashboard.cpuCores')} value={t('dashboard.cores', { count: server.cpu.logical_num })} />
                <InfoRow label={t('dashboard.totalMemory')} value={server.mem.total} />
              </dl>
            ) : (
              <p className="text-muted-foreground">{t('common.loading')}</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function StatCard({ title, value, sub }: { title: string; value: string; sub: string }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm text-muted-foreground">{title}</p>
        <p className="text-3xl font-bold mt-1">{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </CardContent>
    </Card>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  )
}
