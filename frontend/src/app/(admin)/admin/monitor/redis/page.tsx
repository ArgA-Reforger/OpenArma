'use client'

import { useQuery } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface RedisInfo {
  version: string
  mode: string
  role: string
  port: number
  clients: number
  uptime: string
  memory_used: string
  memory_peak: string
  memory_total: string
  memory_usage: string
  connections_received: number
  commands_processed: number
  keyspace_hits: number
  keyspace_misses: number
  hit_rate: string
}

export default function RedisMonitorPage() {
  const api = useApi()
  const { t } = useI18n()

  const { data, isLoading } = useQuery({
    queryKey: ['admin-redis-monitor'],
    queryFn: () => api.get<RedisInfo>('/monitors/redis'),
    refetchInterval: 10000,
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">{t('monitor.redis')}</h1>
        <p className="text-muted-foreground">{t('common.loading')}</p>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('monitor.redis')}</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title={t('dashboard.version')} value={data.version} />
        <StatCard title={t('monitor.mode')} value={data.mode} />
        <StatCard title={t('monitor.role')} value={data.role} />
        <StatCard title={t('monitor.port')} value={String(data.port)} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>{t('monitor.serviceInfo')}</CardTitle></CardHeader>
          <CardContent>
            <DescList items={[
              [t('dashboard.version'), data.version],
              [t('monitor.mode'), data.mode],
              [t('monitor.role'), data.role],
              [t('monitor.port'), String(data.port)],
              [t('dashboard.uptime'), data.uptime],
              [t('monitor.clients'), String(data.clients)],
            ]} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>{t('monitor.memoryInfo')}</CardTitle></CardHeader>
          <CardContent>
            <DescList items={[
              [t('monitor.usedMemory'), data.memory_used],
              [t('monitor.peakMemory'), data.memory_peak],
              [t('monitor.totalMemory'), data.memory_total],
              [t('monitor.memoryUsage'), data.memory_usage],
            ]} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>{t('monitor.statsInfo')}</CardTitle></CardHeader>
          <CardContent>
            <DescList items={[
              [t('monitor.connections'), String(data.connections_received)],
              [t('monitor.commands'), String(data.commands_processed)],
              [t('monitor.hits'), String(data.keyspace_hits)],
              [t('monitor.misses'), String(data.keyspace_misses)],
              [t('monitor.hitRate'), data.hit_rate],
            ]} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm text-muted-foreground">{title}</p>
        <p className="text-2xl font-bold mt-1">{value}</p>
      </CardContent>
    </Card>
  )
}

function DescList({ items }: { items: [string, string][] }) {
  return (
    <dl className="space-y-2">
      {items.map(([label, val]) => (
        <div key={label} className="flex justify-between text-sm">
          <dt className="text-muted-foreground">{label}</dt>
          <dd className="font-medium">{val}</dd>
        </div>
      ))}
    </dl>
  )
}
