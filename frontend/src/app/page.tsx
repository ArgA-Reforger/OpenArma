'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore, useHydrated } from '@/stores/auth'

export default function Home() {
  const router = useRouter()
  const token = useAuthStore((s) => s.token)
  const hydrated = useHydrated()

  useEffect(() => {
    if (hydrated) {
      router.replace(token ? '/projects' : '/login')
    }
  }, [hydrated, token, router])

  return null
}
