'use client'

import { use } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useI18n } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { Play } from 'lucide-react'
import { ChatColumn, type Message } from '@/app/(user)/projects/[id]/chat/chat-column'
import { LocaleSwitcher } from '@/components/locale-switcher'

interface SharedConversation {
  id: number
  title: string | null
  side: string | null
  source: string | null
  messages: Message[]
}

interface SharedData {
  title: string | null
  source: string | null
  is_group: boolean
  conversations: SharedConversation[]
  project_id: number
}

export default function SharedConversationPage({
  params,
}: {
  params: Promise<{ code: string }>
}) {
  const { code } = use(params)
  const { t } = useI18n()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['shared', code],
    queryFn: () => api.get<SharedData>(`/shared/${code}`),
  })

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-bold">{t('shared.invalidLink')}</h1>
          <p className="text-muted-foreground">{t('shared.invalidDesc')}</p>
          <Link href="/login">
            <Button>{t('shared.goLogin')}</Button>
          </Link>
        </div>
      </div>
    )
  }

  const isMulti = data.conversations.length > 1
  const isArma = data.source === 'arma'

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <header className="border-b px-6 py-3 flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-lg font-semibold">{data.title || t('shared.sharedConversation')}</h1>
          <p className="text-xs text-muted-foreground">{t('shared.sharedVia')}</p>
        </div>
        <div className="flex items-center gap-2">
          {isArma && (
            <Link href={`/shared/${code}/replay`}>
              <Button variant="outline" size="sm">
                <Play className="h-3.5 w-3.5 mr-1" />
                {t('replay.title')}
              </Button>
            </Link>
          )}
          <LocaleSwitcher />
          <Link href="/login">
            <Button variant="outline" size="sm">{t('shared.loginToUse')}</Button>
          </Link>
        </div>
      </header>

      <div className="flex-1 min-h-0">
        {isMulti ? (
          <div className={cn(
            'h-full grid',
            data.conversations.length === 2 && 'grid-cols-2',
            data.conversations.length >= 3 && 'grid-cols-3',
          )}>
            {data.conversations.map((conv, idx) => (
              <div
                key={conv.id}
                className={cn('min-h-0 h-full', idx < data.conversations.length - 1 && 'border-r')}
              >
                <ChatColumn
                  pid=""
                  conversationId={conv.id}
                  title={conv.title || conv.side || `Chat ${idx + 1}`}
                  showTitle
                  compact
                  readonly
                  externalMessages={conv.messages}
                  externalSource={conv.source}
                />
              </div>
            ))}
          </div>
        ) : (
          <ChatColumn
            pid=""
            conversationId={data.conversations[0]?.id ?? 0}
            title={data.title}
            readonly
            externalMessages={data.conversations[0]?.messages ?? []}
            externalSource={data.source}
          />
        )}
      </div>

      <footer className="border-t px-6 py-3 text-center shrink-0">
        <p className="text-xs text-muted-foreground">
          {t('shared.poweredBy')}
        </p>
      </footer>
    </div>
  )
}
