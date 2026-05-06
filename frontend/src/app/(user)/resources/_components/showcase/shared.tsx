'use client'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { useAuthStore } from '@/stores/auth'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link2, ShieldCheck, ShieldOff } from 'lucide-react'
import { toast } from 'sonner'

export function VisibilityBadge({ visibility }: { visibility: string }) {
  const { t } = useI18n()
  if (visibility === 'official') {
    return <Badge className="bg-amber-500 hover:bg-amber-600">{t('showcase.official')}</Badge>
  }
  return <Badge variant="secondary">{t('showcase.public')}</Badge>
}

export function BindButton({ onClick }: { onClick: () => void }) {
  const { t } = useI18n()
  return (
    <Button
      variant="outline"
      size="sm"
      className="gap-1.5"
      onClick={(e) => { e.stopPropagation(); onClick() }}
    >
      <Link2 className="h-3.5 w-3.5" />
      {t('showcase.bindToProject')}
    </Button>
  )
}

export function useIsAdmin() {
  const { user } = useAuthStore()
  return user?.is_superuser || user?.is_staff
}

export function OfficialToggle({
  resourceType,
  id,
  visibility,
  queryKey,
}: {
  resourceType: string
  id: number | string
  visibility: string
  queryKey: string[]
}) {
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()
  const isAdmin = useIsAdmin()

  const mutation = useMutation({
    mutationFn: (newVisibility: string) =>
      api.put(`/showcase/${resourceType}/${id}/visibility`, { visibility: newVisibility }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey })
      toast.success(t('showcase.visibilityUpdated'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  if (!isAdmin) return null

  const isOfficial = visibility === 'official'

  return (
    <Button
      variant={isOfficial ? 'secondary' : 'outline'}
      size="sm"
      className="gap-1.5"
      onClick={(e) => {
        e.stopPropagation()
        mutation.mutate(isOfficial ? 'public' : 'official')
      }}
      disabled={mutation.isPending}
    >
      {isOfficial ? <ShieldOff className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}
      {isOfficial ? t('showcase.unsetOfficial') : t('showcase.setOfficial')}
    </Button>
  )
}
