import { useEffect, useState } from 'react'
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface User {
  id: number
  uuid: string
  username: string
  nickname: string
  email: string | null
  avatar: string | null
  is_superuser: boolean
  is_staff: boolean
  status: number
}

interface AuthState {
  token: string | null
  user: User | null
  setAuth: (token: string, user: User) => void
  logout: () => void
  isAuthenticated: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
      isAuthenticated: () => !!get().token,
    }),
    { name: 'openarma-auth' },
  ),
)

export function useHydrated() {
  const [hydrated, setHydrated] = useState(false)
  useEffect(() => {
    const unsub = useAuthStore.persist.onFinishHydration(() => setHydrated(true))
    if (useAuthStore.persist.hasHydrated()) setHydrated(true)
    return unsub
  }, [])
  return hydrated
}
