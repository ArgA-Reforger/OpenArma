'use client'

import { useQuery } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
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

  const { data, isLoading } = useQuery({
    queryKey: ['admin-redis-monitor'],
    queryFn: () => api.get<RedisInfo>('/monitors/redis'),
    refetchInterval: 10000,
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Redis 监控</h1>
        <p className="text-muted-foreground">加载中...</p>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Redis 监控</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="版本" value={data.version} />
        <StatCard title="模式" value={data.mode} />
        <StatCard title="角色" value={data.role} />
        <StatCard title="端口" value={String(data.port)} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>服务信息</CardTitle></CardHeader>
          <CardContent>
            <DescList items={[
              ['版本', data.version],
              ['运行模式', data.mode],
              ['角色', data.role],
              ['端口', String(data.port)],
              ['运行时间', data.uptime],
              ['连接客户端数', String(data.clients)],
            ]} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>内存信息</CardTitle></CardHeader>
          <CardContent>
            <DescList items={[
              ['已使用内存', data.memory_used],
              ['内存峰值', data.memory_peak],
              ['系统总内存', data.memory_total],
              ['内存使用率', data.memory_usage],
            ]} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>统计信息</CardTitle></CardHeader>
          <CardContent>
            <DescList items={[
              ['接收连接数', String(data.connections_received)],
              ['处理命令数', String(data.commands_processed)],
              ['命中次数', String(data.keyspace_hits)],
              ['未命中次数', String(data.keyspace_misses)],
              ['命中率', data.hit_rate],
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
