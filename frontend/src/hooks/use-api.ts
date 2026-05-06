import { useMemo } from 'react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

export function useApi() {
  const token = useAuthStore((s) => s.token)
  return useMemo(() => ({
    get: <T = unknown>(path: string) => api.get<T>(path, { token: token ?? undefined }),
    post: <T = unknown>(path: string, body?: unknown) =>
      api.post<T>(path, body, { token: token ?? undefined }),
    put: <T = unknown>(path: string, body?: unknown) =>
      api.put<T>(path, body, { token: token ?? undefined }),
    delete: <T = unknown>(path: string, body?: unknown) =>
      api.delete<T>(path, body, { token: token ?? undefined }),
    upload: <T = unknown>(path: string, formData: FormData) =>
      api.upload<T>(path, formData, { token: token ?? undefined }),
  }), [token])
}
