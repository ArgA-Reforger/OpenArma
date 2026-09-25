'use client'

import { useQuery } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
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
  const { t } = useI18n()

  const { data, isLoading } = useQuery({
    queryKey: ['admin-server-monitor'],
    queryFn: () => api.get<ServerInfo>('/monitors/server'),
    refetchInterval: 10000,
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">{t('monitor.server')}</h1>
        <p className="text-muted-foreground">{t('common.loading')}</p>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('monitor.server')}</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title={t('dashboard.cpuUsage')} value={`${data.cpu.usage}%`} color={getColor(data.cpu.usage)} />
        <StatCard title={t('dashboard.memUsage')} value={`${data.mem.usage}%`} color={getColor(data.mem.usage)} />
        <StatCard title={t('monitor.logicalCores')} value={String(data.cpu.logical_num)} />
        <StatCard title={t('monitor.physicalCores')} value={String(data.cpu.physical_num)} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>{t('monitor.cpuInfo')}</CardTitle></CardHeader>
          <CardContent>
            <DescList items={[
              [t('monitor.usage'), `${data.cpu.usage}%`],
              [t('monitor.logicalCores'), String(data.cpu.logical_num)],
              [t('monitor.physicalCores'), String(data.cpu.physical_num)],
              [t('monitor.maxFreq'), data.cpu.max_freq],
              [t('monitor.minFreq'), data.cpu.min_freq],
              [t('monitor.currentFreq'), data.cpu.current_freq],
            ]} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>{t('monitor.memInfo')}</CardTitle></CardHeader>
          <CardContent>
            <DescList items={[
              [t('monitor.totalMem'), data.mem.total],
              [t('monitor.usedMem'), data.mem.used],
              [t('monitor.freeMem'), data.mem.free],
              [t('monitor.usage'), `${data.mem.usage}%`],
            ]} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>{t('monitor.sysInfo')}</CardTitle></CardHeader>
          <CardContent>
            <DescList items={[
              [t('monitor.system'), data.sys.name],
              [t('dashboard.version'), data.sys.version],
              [t('monitor.hostname'), data.sys.hostname],
              [t('monitor.bootTime'), data.sys.boot_time],
            ]} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>{t('monitor.serviceInfo')}</CardTitle></CardHeader>
          <CardContent>
            <DescList items={[
              [t('monitor.service'), data.service.name],
              [t('dashboard.version'), data.service.version],
              [t('monitor.python'), data.service.python_version],
              ['PID', String(data.service.pid)],
              [t('dashboard.uptime'), data.service.uptime],
            ]} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>{t('monitor.diskInfo')}</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('monitor.device')}</TableHead>
                <TableHead>{t('monitor.mountpoint')}</TableHead>
                <TableHead>{t('monitor.fstype')}</TableHead>
                <TableHead>{t('monitor.totalSpace')}</TableHead>
                <TableHead>{t('monitor.usedSpace')}</TableHead>
                <TableHead>{t('monitor.freeSpace')}</TableHead>
                <TableHead>{t('monitor.usage')}</TableHead>
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
