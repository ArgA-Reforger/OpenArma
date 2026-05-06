'use client'

import { useEffect } from 'react'
import { useAuthStore } from '@/stores/auth'
import { setOnUnauthorized } from '@/lib/api'

export function AuthGuardProvider({ children }: { children: React.ReactNode }) {
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    setOnUnauthorized(() => {
      logout()
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    })
  }, [logout])

  return <>{children}</>
}
