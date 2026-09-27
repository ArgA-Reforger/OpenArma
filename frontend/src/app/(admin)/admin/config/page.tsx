'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from 'sonner'

interface ConfigItem {
  id: number
  name: string
  type: string
  key: string
  value: string
  is_frontend: boolean
  remark: string | null
}

type ConfigTab = 'USER_SECURITY' | 'LOGIN' | 'EMAIL'

export default function ConfigPage() {
  const api = useApi()
  const qc = useQueryClient()
  const { t } = useI18n()

  const TABS: { key: ConfigTab; label: string }[] = [
    { key: 'USER_SECURITY', label: t('config.userSecurity') },
    { key: 'LOGIN', label: t('config.loginConfig') },
    { key: 'EMAIL', label: t('config.emailConfig') },
  ]
  const [tab, setTab] = useState<ConfigTab>('USER_SECURITY')
  const [editing, setEditing] = useState(false)
  const [formValues, setFormValues] = useState<Record<string, string>>({})

  const { data, isLoading } = useQuery({
    queryKey: ['admin-config', tab],
    queryFn: () => api.get<ConfigItem[]>(`/sys/configs/all?type=${tab}`),
  })

  useEffect(() => {
    if (data) {
      const values: Record<string, string> = {}
      data.forEach((c) => { values[c.key] = c.value })
      setFormValues(values)
      setEditing(false)
    }
  }, [data])

  const saveMutation = useMutation({
    mutationFn: (items: ConfigItem[]) => api.put('/sys/configs', items),
    onSuccess: () => {
      toast.success(t('config.configSaved'))
      qc.invalidateQueries({ queryKey: ['admin-config', tab] })
      setEditing(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  function handleSave() {
    if (!data) return
    const updated = data.map((c) => ({ ...c, value: formValues[c.key] ?? c.value }))
    saveMutation.mutate(updated)
  }

  const isPassword = (key: string) =>
    key.toLowerCase().includes('password') || key.toLowerCase().includes('secret')

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t('config.title')}</h1>

      <div className="flex gap-2 border-b pb-2">
        {TABS.map((t) => (
          <Button
            key={t.key}
            variant={tab === t.key ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </Button>
        ))}
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{TABS.find((t) => t.key === tab)?.label}</CardTitle>
          <div className="flex gap-2">
            {editing ? (
              <>
                <Button variant="outline" size="sm" onClick={() => {
                  if (data) {
                    const values: Record<string, string> = {}
                    data.forEach((c) => { values[c.key] = c.value })
                    setFormValues(values)
                  }
                  setEditing(false)
                }}>
                  {t('common.cancel')}
                </Button>
                <Button size="sm" onClick={handleSave} disabled={saveMutation.isPending}>
                  {saveMutation.isPending ? t('common.saving') : t('common.save')}
                </Button>
              </>
            ) : (
              <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
                {t('common.edit')}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">{t('common.loading')}</p>
          ) : !data?.length ? (
            <p className="text-muted-foreground">{t('config.noConfigItems')}</p>
          ) : (
            <div className="space-y-4">
              {data.map((c) => (
                <div key={c.id} className="grid grid-cols-3 gap-4 items-center">
                  <Label className="text-right text-muted-foreground">
                    {c.name}
                    {c.remark && (
                      <span className="block text-xs font-normal">{c.remark}</span>
                    )}
                  </Label>
                  <div className="col-span-2">
                    {editing ? (
                      isBoolField(c.key) ? (
                        <select
                          value={formValues[c.key] ?? c.value}
                          onChange={(e) => setFormValues((prev) => ({ ...prev, [c.key]: e.target.value }))}
                          className="flex h-9 w-full max-w-xs rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                        >
                          <option value="true">{t('common.yes')}</option>
                          <option value="false">{t('common.no')}</option>
                        </select>
                      ) : (
                        <Input
                          type={isPassword(c.key) ? 'password' : 'text'}
                          value={formValues[c.key] ?? c.value}
                          onChange={(e) => setFormValues((prev) => ({ ...prev, [c.key]: e.target.value }))}
                          className="max-w-xs"
                        />
                      )
                    ) : (
                      <span className="text-sm font-medium">
                        {isPassword(c.key) ? '••••••' : formatValue(c.key, c.value, t)}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function isBoolField(key: string) {
  return key.includes('ENABLED') || key.includes('REQUIRE') || key.includes('SSL') || key === 'USER_SECURITY_CONFIG_STATUS' || key === 'LOGIN_CONFIG_STATUS' || key === 'EMAIL_CONFIG_STATUS'
}

function formatValue(key: string, value: string, t: (key: string) => string) {
  if (isBoolField(key)) return value === 'true' ? t('common.yes') : t('common.no')
  if (value === '1') return t('common.enabled')
  if (value === '0') return t('common.disabled')
  return value
}
