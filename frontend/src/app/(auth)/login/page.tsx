'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { LocaleSwitcher } from '@/components/locale-switcher'
import { LogoIcon } from '@/components/logo'
import { useI18n } from '@/lib/i18n'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import type { User } from '@/stores/auth'

interface CaptchaResponse {
  is_enabled: boolean
  expire_seconds: number
  uuid: string
  image: string
}

interface LoginResponse {
  access_token: string
  access_token_expire_time: string
  session_uuid: string
  user: User
}

export default function LoginPage() {
  const router = useRouter()
  const setAuth = useAuthStore((s) => s.setAuth)
  const { t } = useI18n()
  const [loading, setLoading] = useState(false)
  const [captcha, setCaptcha] = useState<CaptchaResponse | null>(null)
  const [captchaLoading, setCaptchaLoading] = useState(false)

  const fetchCaptcha = useCallback(async () => {
    setCaptchaLoading(true)
    try {
      const data = await api.get<CaptchaResponse>('/auth/captcha')
      setCaptcha(data)
    } catch {
      setCaptcha(null)
    } finally {
      setCaptchaLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCaptcha()
  }, [fetchCaptcha])

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    const formData = new FormData(e.currentTarget)
    const username = formData.get('username') as string
    const password = formData.get('password') as string
    const captchaCode = formData.get('captcha') as string

    try {
      const body: Record<string, string> = { username, password }
      if (captcha?.is_enabled) {
        body.uuid = captcha.uuid
        body.captcha = captchaCode
      }
      const data = await api.post<LoginResponse>('/auth/login', body)
      setAuth(data.access_token, data.user)
      toast.success(t('auth.loginSuccess'))
      router.push('/projects')
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : t('auth.loginFailed')
      toast.error(message)
      fetchCaptcha()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-2">
            <LogoIcon size={56} />
          </div>
          <CardTitle className="text-2xl">
            <span className="font-extrabold">OPEN</span>
            <span className="font-light text-muted-foreground">ARMA</span>
          </CardTitle>
          <CardDescription>{t('auth.subtitle')}</CardDescription>
          <div className="flex justify-center mt-2">
            <LocaleSwitcher />
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">{t('auth.username')}</Label>
              <Input id="username" name="username" required autoFocus placeholder={t('auth.enterUsername')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{t('auth.password')}</Label>
              <Input id="password" name="password" type="password" required placeholder={t('auth.enterPassword')} />
            </div>
            {captcha?.is_enabled && (
              <div className="space-y-2">
                <Label htmlFor="captcha">{t('auth.captcha')}</Label>
                <div className="flex gap-3">
                  <Input
                    id="captcha"
                    name="captcha"
                    required
                    placeholder={t('auth.enterCaptcha')}
                    className="flex-1"
                    autoComplete="off"
                  />
                  <button
                    type="button"
                    onClick={fetchCaptcha}
                    className="h-9 shrink-0 cursor-pointer overflow-hidden rounded-md border"
                    title={t('auth.refreshCaptcha')}
                    aria-label={t('auth.refreshCaptcha')}
                    disabled={captchaLoading}
                  >
                    {captcha.image ? (
                      <Image
                        src={`data:image/png;base64,${captcha.image}`}
                        alt={t('auth.captcha')}
                        width={120}
                        height={36}
                        className="h-full w-auto"
                        unoptimized
                      />
                    ) : (
                      <span className="px-3 text-xs text-muted-foreground">{t('common.loading')}</span>
                    )}
                  </button>
                </div>
              </div>
            )}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? t('auth.loggingIn') : t('auth.login')}
            </Button>
          </form>
          <div className="mt-4">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <Separator />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground">{t('auth.orLoginWith')}</span>
              </div>
            </div>
            <div className="mt-4 flex gap-3">
              {/* TODO: Enable GitHub OAuth when client credentials are configured */}
              {/* <OAuthButton provider="github" label="GitHub" /> */}
              <OAuthButton provider="google" label="Google" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function OAuthButton({ provider, label }: { provider: string; label: string }) {
  const [loading, setLoading] = useState(false)
  const { t } = useI18n()

  async function handleClick() {
    setLoading(true)
    try {
      const url = await api.get<string>(`/oauth2/${provider}`)
      window.location.href = url
    } catch {
      toast.error(t('auth.oauthUnavailable', { provider: label }))
      setLoading(false)
    }
  }

  return (
    <Button
      variant="outline"
      className="flex-1"
      onClick={handleClick}
      disabled={loading}
    >
      {loading ? t('auth.redirecting') : label}
    </Button>
  )
}
