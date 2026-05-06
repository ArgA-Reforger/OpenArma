'use client'

import { useQuery } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface ServerInfo {
  cpu: { usage: number; logical_num: number }
  mem: { total: string; used: string; usage: number }
  service: { name: string; version: string; uptime: string }
}

export default function AdminDashboard() {
  const api = useApi()

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
      <h1 className="text-2xl font-bold">系统概览</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="CPU 使用率"
          value={server ? `${server.cpu.usage}%` : '-'}
          sub={server ? `${server.cpu.logical_num} 核` : ''}
        />
        <StatCard
          title="内存使用率"
          value={server ? `${server.mem.usage}%` : '-'}
          sub={server ? `${server.mem.used} / ${server.mem.total}` : ''}
        />
        <StatCard
          title="在线用户"
          value={online ? String(online.length) : '-'}
          sub="当前活跃会话"
        />
        <StatCard
          title="服务运行时间"
          value={server?.service.uptime ?? '-'}
          sub={server ? `${server.service.name} ${server.service.version}` : ''}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>快捷导航</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2">
              {[
                { href: '/admin/users', label: '用户管理' },
                { href: '/admin/roles', label: '角色管理' },
                { href: '/admin/logs/login', label: '登录日志' },
                { href: '/admin/logs/opera', label: '操作日志' },
                { href: '/admin/monitor/online', label: '在线用户' },
                { href: '/admin/monitor/server', label: '服务器监控' },
                { href: '/admin/monitor/redis', label: 'Redis 监控' },
                { href: '/admin/config', label: '系统配置' },
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
          <CardHeader><CardTitle>系统信息</CardTitle></CardHeader>
          <CardContent>
            {server ? (
              <dl className="space-y-2">
                <InfoRow label="服务名称" value={server.service.name} />
                <InfoRow label="版本" value={server.service.version} />
                <InfoRow label="运行时间" value={server.service.uptime} />
                <InfoRow label="CPU 核心" value={`${server.cpu.logical_num} 核`} />
                <InfoRow label="总内存" value={server.mem.total} />
              </dl>
            ) : (
              <p className="text-muted-foreground">加载中...</p>
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
