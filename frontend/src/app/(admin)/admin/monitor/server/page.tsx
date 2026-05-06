'use client'

import { useQuery } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'

interface ServerInfo {
  cpu: {
    usage: number
    logical_num: number
    physical_num: number
    max_freq: string
    min_freq: string
    current_freq: string
  }
  mem: {
    total: string
    used: string
    free: string
    usage: number
  }
  sys: {
    name: string
    version: string
    hostname: string
    boot_time: string
  }
  service: {
    name: string
    version: string
    python_version: string
    pid: number
    uptime: string
  }
  disk: Array<{
    device: string
    mountpoint: string
    fstype: string
    total: string
    used: string
    free: string
    usage: number
  }>
}

export default function ServerMonitorPage() {
  const api = useApi()

  const { data, isLoading } = useQuery({
    queryKey: ['admin-server-monitor'],
    queryFn: () => api.get<ServerInfo>('/monitors/server'),
    refetchInterval: 10000,
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">服务器监控</h1>
        <p className="text-muted-foreground">加载中...</p>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">服务器监控</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="CPU 使用率" value={`${data.cpu.usage}%`} color={getColor(data.cpu.usage)} />
        <StatCard title="内存使用率" value={`${data.mem.usage}%`} color={getColor(data.mem.usage)} />
        <StatCard title="逻辑核心" value={String(data.cpu.logical_num)} />
        <StatCard title="物理核心" value={String(data.cpu.physical_num)} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>CPU 信息</CardTitle></CardHeader>
          <CardContent>
            <DescList items={[
              ['使用率', `${data.cpu.usage}%`],
              ['逻辑核心', String(data.cpu.logical_num)],
              ['物理核心', String(data.cpu.physical_num)],
              ['最大频率', data.cpu.max_freq],
              ['最小频率', data.cpu.min_freq],
              ['当前频率', data.cpu.current_freq],
            ]} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>内存信息</CardTitle></CardHeader>
          <CardContent>
            <DescList items={[
              ['总内存', data.mem.total],
              ['已使用', data.mem.used],
              ['可用', data.mem.free],
              ['使用率', `${data.mem.usage}%`],
            ]} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>系统信息</CardTitle></CardHeader>
          <CardContent>
            <DescList items={[
              ['系统', data.sys.name],
              ['版本', data.sys.version],
              ['主机名', data.sys.hostname],
              ['启动时间', data.sys.boot_time],
            ]} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>服务信息</CardTitle></CardHeader>
          <CardContent>
            <DescList items={[
              ['服务', data.service.name],
              ['版本', data.service.version],
              ['Python', data.service.python_version],
              ['PID', String(data.service.pid)],
              ['运行时间', data.service.uptime],
            ]} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>磁盘信息</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>设备</TableHead>
                <TableHead>挂载点</TableHead>
                <TableHead>文件系统</TableHead>
                <TableHead>总容量</TableHead>
                <TableHead>已使用</TableHead>
                <TableHead>可用</TableHead>
                <TableHead>使用率</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.disk.map((d, i) => (
                <TableRow key={i}>
                  <TableCell>{d.device}</TableCell>
                  <TableCell>{d.mountpoint}</TableCell>
                  <TableCell>{d.fstype}</TableCell>
                  <TableCell>{d.total}</TableCell>
                  <TableCell>{d.used}</TableCell>
                  <TableCell>{d.free}</TableCell>
                  <TableCell>
                    <span className={d.usage > 80 ? 'text-destructive font-medium' : ''}>
                      {d.usage}%
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

function StatCard({ title, value, color }: { title: string; value: string; color?: string }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm text-muted-foreground">{title}</p>
        <p className={`text-3xl font-bold mt-1 ${color ?? ''}`}>{value}</p>
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

function getColor(usage: number) {
  if (usage > 80) return 'text-destructive'
  if (usage > 60) return 'text-yellow-600'
  return 'text-green-600'
}
