'use client'

import { Suspense, useEffect, useRef } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/lib/api'
import { toast } from 'sonner'
import { useI18n } from '@/lib/i18n'
import type { User } from '@/stores/auth'

function CallbackHandler() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const setAuth = useAuthStore((s) => s.setAuth)
  const processed = useRef(false)
  const { t } = useI18n()

  useEffect(() => {
    if (processed.current) return
    processed.current = true

    const accessToken = searchParams.get('access_token')
    const sessionUuid = searchParams.get('session_uuid')

    if (!accessToken || !sessionUuid) {
      toast.error(t('auth.oauthFailed'))
      router.replace('/login')
      return
    }

    api
      .get<User>('/sys/users/me', { token: accessToken })
      .then((user) => {
        setAuth(accessToken, user)
        toast.success(t('auth.loginSuccess'))
        router.replace('/projects')
      })
      .catch(() => {
        toast.error(t('auth.oauthFailed'))
        router.replace('/login')
      })
  }, [searchParams, setAuth, router, t])

  return (
    <div className="text-center">
      <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto" />
      <p className="mt-4 text-muted-foreground">{t('auth.authenticating')}</p>
    </div>
  )
}

export default function OAuth2CallbackPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Suspense fallback={
        <div className="text-center">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto" />
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      }>
        <CallbackHandler />
      </Suspense>
    </div>
  )
}
