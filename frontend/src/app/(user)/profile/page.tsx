'use client'

import { useState, useMemo } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { toast } from 'sonner'
import { useI18n } from '@/lib/i18n'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  Activity, Zap, ArrowUpRight, ArrowDownRight, DollarSign, Database, Brain,
  ChevronLeft, ChevronRight, User, Shield, KeyRound, Link2, Link2Off,
} from 'lucide-react'

type UsageTab = 'records' | 'provider' | 'project' | 'daily'

interface SummaryData {
  total_calls: number
  total_prompt_tokens: number
  total_completion_tokens: number
  total_tokens: number
  total_cached_tokens: number
  total_reasoning_tokens: number
  estimated_cost: number
}

interface ProviderRow {
  provider_type: string
  provider_name: string
  model_name: string
  calls: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  cached_tokens: number
  reasoning_tokens: number
  cost: number
}

interface ProjectRow {
  project_id: number | null
  project_name: string
  calls: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  cost: number
}

interface DailyRow {
  date: string
  calls: number
  total_tokens: number
  cost: number
}

interface RecordRow {
  id: string
  provider_type: string
  provider_name: string
  model_name: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  cached_tokens: number
  reasoning_tokens: number
  estimated_cost: number
  currency: string
  call_type: string
  status: string
  error_message: string | null
  duration_ms: number | null
  project_name: string
  agent_name: string
  created_time: string
}

interface RecordsData {
  total: number
  page: number
  size: number
  items: RecordRow[]
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

function defaultDateRange(): { start: string; end: string } {
  const now = new Date()
  const end = now.toISOString().slice(0, 10)
  const start = new Date(now.getTime() - 30 * 86400000).toISOString().slice(0, 10)
  return { start, end }
}

export default function ProfilePage() {
  const api = useApi()
  const { user, setAuth, token } = useAuthStore()
  const { t } = useI18n()

  const [nicknameOpen, setNicknameOpen] = useState(false)
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [unbindTarget, setUnbindTarget] = useState<string | null>(null)

  const defaults = useMemo(defaultDateRange, [])
  const [startDate, setStartDate] = useState(defaults.start)
  const [endDate, setEndDate] = useState(defaults.end)
  const [usageTab, setUsageTab] = useState<UsageTab>('records')
  const [recordsPage, setRecordsPage] = useState(1)

  const qs = `start_date=${startDate}&end_date=${endDate}`

  const { data: summary, isLoading: summaryLoading } = useQuery<SummaryData>({
    queryKey: ['usage-summary', startDate, endDate],
    queryFn: () => api.get(`/usage/summary?${qs}`),
  })

  const { data: recordsData, isLoading: recordsLoading } = useQuery<RecordsData>({
    queryKey: ['usage-records', startDate, endDate, recordsPage],
    queryFn: () => api.get(`/usage/records?${qs}&page=${recordsPage}&size=20`),
    enabled: usageTab === 'records',
  })

  const { data: providerData, isLoading: providerLoading } = useQuery<ProviderRow[]>({
    queryKey: ['usage-provider', startDate, endDate],
    queryFn: () => api.get(`/usage/by-provider?${qs}`),
    enabled: usageTab === 'provider',
  })

  const { data: projectData, isLoading: projectLoading } = useQuery<ProjectRow[]>({
    queryKey: ['usage-project', startDate, endDate],
    queryFn: () => api.get(`/usage/by-project?${qs}`),
    enabled: usageTab === 'project',
  })

  const { data: dailyData, isLoading: dailyLoading } = useQuery<DailyRow[]>({
    queryKey: ['usage-daily', startDate, endDate],
    queryFn: () => api.get(`/usage/daily?${qs}`),
    enabled: usageTab === 'daily',
  })

  const maxDailyTokens = useMemo(() => {
    if (!dailyData?.length) return 1
    return Math.max(...dailyData.map((d) => d.total_tokens), 1)
  }, [dailyData])

  const nicknameMutation = useMutation({
    mutationFn: (nickname: string) => api.put('/sys/users/me/nickname', { nickname }),
    onSuccess: (_, nickname) => {
      if (user && token) setAuth(token, { ...user, nickname })
      toast.success(t('profile.nicknameUpdated'))
      setNicknameOpen(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const passwordMutation = useMutation({
    mutationFn: (body: { old_password: string; new_password: string; confirm_password: string }) =>
      api.put('/sys/users/me/password', body),
    onSuccess: () => {
      toast.success(t('profile.passwordUpdated'))
      setPasswordOpen(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const { data: oauthBindings, refetch: refetchBindings } = useQuery<string[]>({
    queryKey: ['oauth-bindings'],
    queryFn: () => api.get('/oauth2/me/bindings'),
  })

  const unbindMutation = useMutation({
    mutationFn: (source: string) => api.delete(`/oauth2/me/unbinding?source=${source}`),
    onSuccess: () => {
      toast.success(t('profile.unbindSuccess'))
      refetchBindings()
      setUnbindTarget(null)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const handleBind = async (source: string) => {
    try {
      const url = await api.get<string>(`/oauth2/me/binding?source=${source}`)
      window.location.href = url
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed')
    }
  }

  if (!user) return null

  const summaryCards = [
    { label: t('usage.totalCalls'), value: summary?.total_calls, icon: Activity },
    { label: t('usage.totalTokens'), value: summary?.total_tokens, icon: Zap },
    { label: t('usage.promptTokens'), value: summary?.total_prompt_tokens, icon: ArrowUpRight },
    { label: t('usage.completionTokens'), value: summary?.total_completion_tokens, icon: ArrowDownRight },
    { label: t('usage.cachedTokens'), value: summary?.total_cached_tokens, icon: Database },
    { label: t('usage.reasoningTokens'), value: summary?.total_reasoning_tokens, icon: Brain },
    { label: t('usage.estimatedCost'), value: summary?.estimated_cost, icon: DollarSign, isCost: true },
  ]

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      <div className="p-6 space-y-8 max-w-5xl">
        {/* ── Usage Stats ── */}
        <section className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <h2 className="text-lg font-semibold">{t('usage.title')}</h2>
            <div className="flex items-center gap-2">
              <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="w-36 h-8 text-xs" />
              <span className="text-muted-foreground text-sm">—</span>
              <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="w-36 h-8 text-xs" />
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {summaryCards.map((c) => (
              <Card key={c.label}>
                <CardContent className="p-3">
                  <div className="flex items-center gap-1.5 text-muted-foreground text-xs mb-1">
                    <c.icon className="h-3.5 w-3.5" />
                    {c.label}
                  </div>
                  {summaryLoading ? (
                    <Skeleton className="h-6 w-16" />
                  ) : (
                    <p className="text-lg font-bold">
                      {c.isCost ? `$${(c.value ?? 0).toFixed(4)}` : formatNumber(c.value ?? 0)}
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="flex gap-1 border-b">
            {(['records', 'provider', 'project', 'daily'] as UsageTab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setUsageTab(tab)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  usageTab === tab
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                {tab === 'records' ? t('usage.callRecords') : tab === 'provider' ? t('usage.byProvider') : tab === 'project' ? t('usage.byProject') : t('usage.dailyTrend')}
              </button>
            ))}
          </div>

          {usageTab === 'records' && (
            <Card>
              <CardContent className="p-4">
                {recordsLoading ? (
                  <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}</div>
                ) : !recordsData?.items?.length ? (
                  <p className="text-muted-foreground text-sm text-center py-8">{t('usage.noData')}</p>
                ) : (
                  <>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>{t('usage.time')}</TableHead>
                          <TableHead>{t('usage.callTypeLabel')}</TableHead>
                          <TableHead>{t('usage.providerName')}</TableHead>
                          <TableHead>{t('usage.modelName')}</TableHead>
                          <TableHead>{t('usage.statusLabel')}</TableHead>
                          <TableHead className="text-right">{t('usage.promptTokens')}</TableHead>
                          <TableHead className="text-right">{t('usage.cachedTokens')}</TableHead>
                          <TableHead className="text-right">{t('usage.completionTokens')}</TableHead>
                          <TableHead className="text-right">{t('usage.reasoningTokens')}</TableHead>
                          <TableHead className="text-right">{t('usage.totalTokens')}</TableHead>
                          <TableHead className="text-right">{t('usage.cost')}</TableHead>
                          <TableHead className="text-right">{t('usage.durationLabel')}</TableHead>
                          <TableHead>{t('usage.projectName')}</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {recordsData.items.map((r) => (
                          <TableRow key={r.id} className={r.status === 'failed' ? 'bg-destructive/5' : ''}>
                            <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                              {new Date(r.created_time).toLocaleString()}
                            </TableCell>
                            <TableCell>
                              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${
                                r.call_type === 'chat' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                                : r.call_type === 'title_gen' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                                : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                              }`}>
                                {r.call_type}
                              </span>
                            </TableCell>
                            <TableCell className="text-sm">{r.provider_name}</TableCell>
                            <TableCell className="text-sm">{r.model_name}</TableCell>
                            <TableCell>
                              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${
                                r.status === 'success' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                : r.status === 'partial' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                                : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                              }`}>
                                {r.status}
                              </span>
                              {r.error_message && (
                                <span className="block text-xs text-destructive mt-0.5 max-w-[200px] truncate" title={r.error_message}>
                                  {r.error_message}
                                </span>
                              )}
                            </TableCell>
                            <TableCell className="text-right">{formatNumber(r.prompt_tokens)}</TableCell>
                            <TableCell className="text-right text-muted-foreground">
                              {r.cached_tokens > 0 ? formatNumber(r.cached_tokens) : '-'}
                            </TableCell>
                            <TableCell className="text-right">{formatNumber(r.completion_tokens)}</TableCell>
                            <TableCell className="text-right text-muted-foreground">
                              {r.reasoning_tokens > 0 ? formatNumber(r.reasoning_tokens) : '-'}
                            </TableCell>
                            <TableCell className="text-right font-medium">{formatNumber(r.total_tokens)}</TableCell>
                            <TableCell className="text-right text-muted-foreground">
                              {r.estimated_cost > 0 ? `${r.currency === 'CNY' ? '¥' : '$'}${r.estimated_cost.toFixed(6)}` : '-'}
                            </TableCell>
                            <TableCell className="text-right text-muted-foreground">
                              {r.duration_ms != null ? `${(r.duration_ms / 1000).toFixed(1)}s` : '-'}
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground">{r.project_name}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                    {recordsData.total > recordsData.size && (
                      <div className="flex items-center justify-between mt-4 text-sm">
                        <span className="text-muted-foreground">
                          {t('usage.pageInfo', { page: recordsData.page, total: Math.ceil(recordsData.total / recordsData.size) })}
                        </span>
                        <div className="flex gap-1">
                          <Button variant="outline" size="sm" disabled={recordsPage <= 1} onClick={() => setRecordsPage((p) => p - 1)}>
                            <ChevronLeft className="h-4 w-4" />
                          </Button>
                          <Button variant="outline" size="sm" disabled={recordsPage >= Math.ceil(recordsData.total / recordsData.size)} onClick={() => setRecordsPage((p) => p + 1)}>
                            <ChevronRight className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {usageTab === 'provider' && (
            <Card>
              <CardContent className="p-4">
                {providerLoading ? (
                  <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}</div>
                ) : !providerData?.length ? (
                  <p className="text-muted-foreground text-sm text-center py-8">{t('usage.noData')}</p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t('usage.providerName')}</TableHead>
                        <TableHead>{t('usage.modelName')}</TableHead>
                        <TableHead className="text-right">{t('usage.calls')}</TableHead>
                        <TableHead className="text-right">{t('usage.promptTokens')}</TableHead>
                        <TableHead className="text-right">{t('usage.cachedTokens')}</TableHead>
                        <TableHead className="text-right">{t('usage.completionTokens')}</TableHead>
                        <TableHead className="text-right">{t('usage.reasoningTokens')}</TableHead>
                        <TableHead className="text-right">{t('usage.totalTokens')}</TableHead>
                        <TableHead className="text-right">{t('usage.cost')}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {providerData.map((r, i) => (
                        <TableRow key={i}>
                          <TableCell className="font-medium">{r.provider_name}</TableCell>
                          <TableCell>{r.model_name}</TableCell>
                          <TableCell className="text-right">{formatNumber(r.calls)}</TableCell>
                          <TableCell className="text-right">{formatNumber(r.prompt_tokens)}</TableCell>
                          <TableCell className="text-right text-muted-foreground">
                            {r.cached_tokens > 0 ? formatNumber(r.cached_tokens) : '-'}
                          </TableCell>
                          <TableCell className="text-right">{formatNumber(r.completion_tokens)}</TableCell>
                          <TableCell className="text-right text-muted-foreground">
                            {r.reasoning_tokens > 0 ? formatNumber(r.reasoning_tokens) : '-'}
                          </TableCell>
                          <TableCell className="text-right font-medium">{formatNumber(r.total_tokens)}</TableCell>
                          <TableCell className="text-right">${r.cost.toFixed(4)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          )}

          {usageTab === 'project' && (
            <Card>
              <CardContent className="p-4">
                {projectLoading ? (
                  <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}</div>
                ) : !projectData?.length ? (
                  <p className="text-muted-foreground text-sm text-center py-8">{t('usage.noData')}</p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t('usage.projectName')}</TableHead>
                        <TableHead className="text-right">{t('usage.calls')}</TableHead>
                        <TableHead className="text-right">{t('usage.promptTokens')}</TableHead>
                        <TableHead className="text-right">{t('usage.completionTokens')}</TableHead>
                        <TableHead className="text-right">{t('usage.totalTokens')}</TableHead>
                        <TableHead className="text-right">{t('usage.cost')}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {projectData.map((r, i) => (
                        <TableRow key={i}>
                          <TableCell className="font-medium">{r.project_name}</TableCell>
                          <TableCell className="text-right">{formatNumber(r.calls)}</TableCell>
                          <TableCell className="text-right">{formatNumber(r.prompt_tokens)}</TableCell>
                          <TableCell className="text-right">{formatNumber(r.completion_tokens)}</TableCell>
                          <TableCell className="text-right font-medium">{formatNumber(r.total_tokens)}</TableCell>
                          <TableCell className="text-right">${r.cost.toFixed(4)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          )}

          {usageTab === 'daily' && (
            <Card>
              <CardContent className="p-4">
                {dailyLoading ? (
                  <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-8 w-full" />)}</div>
                ) : !dailyData?.length ? (
                  <p className="text-muted-foreground text-sm text-center py-8">{t('usage.noData')}</p>
                ) : (
                  <div className="space-y-1.5">
                    {dailyData.map((d) => (
                      <div key={d.date} className="flex items-center gap-3 text-sm">
                        <span className="w-24 text-muted-foreground shrink-0">{d.date}</span>
                        <div className="flex-1 h-6 bg-muted rounded-sm overflow-hidden">
                          <div
                            className="h-full bg-primary/80 rounded-sm transition-all"
                            style={{ width: `${(d.total_tokens / maxDailyTokens) * 100}%` }}
                          />
                        </div>
                        <span className="w-16 text-right font-medium shrink-0">{formatNumber(d.total_tokens)}</span>
                        <span className="w-12 text-right text-muted-foreground shrink-0">{d.calls}x</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </section>

        {/* ── Account Info ── */}
        <section className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4 text-muted-foreground" />
                <CardTitle className="text-base">{t('profile.basicInfo')}</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t('profile.username')}</span>
                <span className="font-medium">{user.username}</span>
              </div>
              <Separator />
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t('profile.email')}</span>
                <span className="font-medium">{user.email || '-'}</span>
              </div>
              <Separator />
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">{t('profile.nickname')}</span>
                <div className="flex items-center gap-2">
                  <span className="font-medium">{user.nickname || '-'}</span>
                  <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={() => setNicknameOpen(true)}>{t('common.edit')}</Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-muted-foreground" />
                <CardTitle className="text-base">{t('profile.security')}</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <KeyRound className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">{t('profile.loginPassword')}</p>
                    <p className="text-xs text-muted-foreground">{t('profile.passwordTip')}</p>
                  </div>
                </div>
                <Button variant="outline" size="sm" onClick={() => setPasswordOpen(true)}>{t('profile.changePassword')}</Button>
              </div>
              <Separator />
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Link2 className="h-4 w-4 text-muted-foreground" />
                  <p className="text-sm font-medium">{t('profile.socialAccounts')}</p>
                </div>
                {/* Google — only supported provider currently */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <svg className="h-4 w-4" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
                    <div>
                      <p className="text-sm font-medium">Google</p>
                      <p className="text-xs text-muted-foreground">
                        {oauthBindings?.includes('Google') ? t('profile.bound') : t('profile.notBound')}
                      </p>
                    </div>
                  </div>
                  {oauthBindings?.includes('Google') ? (
                    <Button variant="outline" size="sm" onClick={() => setUnbindTarget('Google')}>
                      <Link2Off className="h-3.5 w-3.5 mr-1.5" />{t('profile.unbind')}
                    </Button>
                  ) : (
                    <Button variant="outline" size="sm" onClick={() => handleBind('Google')}>
                      <Link2 className="h-3.5 w-3.5 mr-1.5" />{t('profile.bind')}
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </section>
      </div>

      <Dialog open={nicknameOpen} onOpenChange={setNicknameOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{t('profile.changeNickname')}</DialogTitle></DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault()
            const fd = new FormData(e.currentTarget)
            nicknameMutation.mutate(fd.get('nickname') as string)
          }} className="space-y-4">
            <div className="space-y-2">
              <Label>{t('profile.newNickname')}</Label>
              <Input name="nickname" required defaultValue={user.nickname} />
            </div>
            <DialogFooter>
              <Button type="submit" disabled={nicknameMutation.isPending}>
                {nicknameMutation.isPending ? t('common.saving') : t('common.save')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!unbindTarget} onOpenChange={(open) => { if (!open) setUnbindTarget(null) }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('profile.unbind')}</AlertDialogTitle>
            <AlertDialogDescription>{t('profile.unbindConfirm')}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={() => unbindTarget && unbindMutation.mutate(unbindTarget)}>
              {t('profile.unbind')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={passwordOpen} onOpenChange={setPasswordOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{t('profile.changePassword')}</DialogTitle></DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault()
            const fd = new FormData(e.currentTarget)
            const newPwd = fd.get('new_password') as string
            const confirmPwd = fd.get('confirm_password') as string
            if (newPwd !== confirmPwd) {
              toast.error(t('profile.passwordMismatch'))
              return
            }
            passwordMutation.mutate({
              old_password: fd.get('old_password') as string,
              new_password: newPwd,
              confirm_password: confirmPwd,
            })
          }} className="space-y-4">
            <div className="space-y-2"><Label>{t('profile.currentPassword')}</Label><Input name="old_password" type="password" required /></div>
            <div className="space-y-2"><Label>{t('profile.newPassword')}</Label><Input name="new_password" type="password" required minLength={6} /></div>
            <div className="space-y-2"><Label>{t('profile.confirmPassword')}</Label><Input name="confirm_password" type="password" required minLength={6} /></div>
            <DialogFooter>
              <Button type="submit" disabled={passwordMutation.isPending}>
                {passwordMutation.isPending ? t('common.saving') : t('profile.confirmChange')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
