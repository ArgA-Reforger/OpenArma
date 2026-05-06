'use client'

import { useI18n } from '@/lib/i18n'
import { MessageSquare } from 'lucide-react'

export default function ProjectsPage() {
  const { t } = useI18n()

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground space-y-3 p-6">
        <MessageSquare className="h-12 w-12 opacity-30" />
        <p className="text-lg">{t('project.emptyHint')}</p>
      </div>
    </div>
  )
}
