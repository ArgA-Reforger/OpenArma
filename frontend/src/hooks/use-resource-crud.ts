import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import type { PageData } from '@/types/resources'

export interface UseResourceCRUDOptions {
  endpoint: string
  queryKey: string[]
  toastKeys?: {
    created?: string
    updated?: string
    deleted?: string
    cloned?: string
  }
  onCreateSuccess?: () => void
  onUpdateSuccess?: () => void
  onDeleteSuccess?: () => void
  onCloneSuccess?: () => void
}

export function useResourceCRUD<T>({
  endpoint,
  queryKey,
  toastKeys,
  onCreateSuccess,
  onUpdateSuccess,
  onDeleteSuccess,
  onCloneSuccess,
}: UseResourceCRUDOptions) {
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()

  const { data, isLoading, isError } = useQuery({
    queryKey,
    queryFn: () => api.get<PageData<T>>(endpoint),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey })

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post(endpoint, body),
    onSuccess: () => {
      invalidate()
      if (toastKeys?.created) toast.success(t(toastKeys.created))
      onCreateSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Record<string, unknown> }) =>
      api.put(`${endpoint}/${id}`, body),
    onSuccess: () => {
      invalidate()
      if (toastKeys?.updated) toast.success(t(toastKeys.updated))
      onUpdateSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`${endpoint}/${id}`),
    onSuccess: () => {
      invalidate()
      if (toastKeys?.deleted) toast.success(t(toastKeys.deleted))
      onDeleteSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const cloneMutation = useMutation({
    mutationFn: (id: number | string) => api.post(`${endpoint}/${id}/clone`),
    onSuccess: () => {
      invalidate()
      if (toastKeys?.cloned) toast.success(t(toastKeys.cloned))
      onCloneSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })

  return {
    data,
    items: data?.items ?? [],
    total: data?.total ?? 0,
    isLoading,
    isError,
    createMutation,
    updateMutation,
    deleteMutation,
    cloneMutation,
    invalidate,
  }
}
