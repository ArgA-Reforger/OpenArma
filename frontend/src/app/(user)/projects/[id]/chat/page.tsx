'use client'

import { use, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { useProjectNavStore } from '@/stores/project-nav'
import { cn } from '@/lib/utils'
import { useI18n } from '@/lib/i18n'
import { PanelRightOpen, PanelRightClose, Settings2, MessageSquare, PlayCircle } from 'lucide-react'
import Link from 'next/link'
import {
  ProjectSettingsPanel, ArmaSettingsTab,
} from './conversation-settings'
import { ChatColumn } from './chat-column'

interface ConvItem {
  id: number | string
  title: string | null
  source: string
  status: string
  side?: string | null
  conversation_group_id?: number | string | null
  agent_id?: number | string | null
  topology_id?: number | string | null
  mission_objective?: Record<string, unknown> | null
}

interface ChatGroup {
  id: string
  convs: ConvItem[]
  isMulti: boolean
}

function buildChatGroups(items: ConvItem[]): ChatGroup[] {
  const groupMap = new Map<string, ConvItem[]>()
  const solo: ConvItem[] = []
  for (const c of items) {
    const gid = c.conversation_group_id
    if (gid) {
      const key = String(gid)
      const arr = groupMap.get(key)
      if (arr) arr.push(c)
      else groupMap.set(key, [c])
    } else {
      solo.push(c)
    }
  }
  const groups: ChatGroup[] = []
  for (const [key, convs] of groupMap) {
    groups.push({ id: `group-${key}`, convs, isMulti: convs.length > 1 })
  }
  for (const c of solo) {
    groups.push({ id: String(c.id), convs: [c], isMulti: false })
  }
  return groups
}

type RightTab = 'conversation' | 'project'

export default function ChatPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: pid } = use(params)
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()
  const { activeConvId } = useProjectNavStore()

  const { data: activeConvDetail, refetch: refetchConvDetail } = useQuery({
    queryKey: ['conv-detail', pid, activeConvId],
    queryFn: () => api.get<ConvItem>(`/projects/${pid}/conversations/${activeConvId}`),
    enabled: !!activeConvId,
    staleTime: 10_000,
  })

  const { data: allConversations } = useQuery({
    queryKey: ['conversations', pid],
    queryFn: () => api.get<{ items: ConvItem[] }>(`/projects/${pid}/conversations?status=active`),
    staleTime: 10_000,
  })

  const groups = useMemo(
    () => buildChatGroups(allConversations?.items ?? []),
    [allConversations],
  )

  const activeGroup = useMemo(
    () => groups.find((g) => g.convs.some((c) => String(c.id) === String(activeConvId))) ?? null,
    [groups, activeConvId],
  )

  const [settingsOpen, setSettingsOpen] = useState(true)
  const [rightTab, setRightTab] = useState<RightTab>('conversation')

  const isMultiConv = activeGroup?.isMulti ?? false
  const displayConversations = isMultiConv ? (activeGroup?.convs ?? []) : []

  const effectiveGroupId = activeConvDetail?.conversation_group_id ?? null

  if (!activeConvId) {
    return (
      <div className="flex-1 flex items-center justify-center h-full text-muted-foreground">
        {t('chat.selectHint')}
      </div>
    )
  }

  const settingsPanel = (
    <div className="h-full flex flex-col border-l bg-background">
      <div className="flex items-center justify-between px-4 py-2 border-b shrink-0">
        <div className="flex border rounded-md overflow-hidden text-xs">
          <button
            onClick={() => setRightTab('conversation')}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 transition-colors',
              rightTab === 'conversation'
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-muted text-muted-foreground',
            )}
          >
            <MessageSquare className="h-3.5 w-3.5" />
            {t('chat.conversationSettings')}
          </button>
          <button
            onClick={() => setRightTab('project')}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 transition-colors',
              rightTab === 'project'
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-muted text-muted-foreground',
            )}
          >
            <Settings2 className="h-3.5 w-3.5" />
            {t('project.projectSettings')}
          </button>
        </div>
        <button
          onClick={() => setSettingsOpen(false)}
          className="p-1.5 rounded-md hover:bg-accent text-muted-foreground"
        >
          <PanelRightClose className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {rightTab === 'conversation' ? (
          <div className="p-4 space-y-4">
            <Link
              href={`/projects/${pid}/replay${effectiveGroupId ? `?group=${effectiveGroupId}` : ''}`}
              className="flex items-center gap-2 w-full rounded-md border bg-muted/30 px-3 py-2 text-sm hover:bg-muted/60 transition-colors"
            >
              <PlayCircle className="h-4 w-4 text-green-500" />
              <span className="font-medium">{t('replay.openReplay')}</span>
            </Link>
            <ArmaSettingsTab
              key={`arma-${effectiveGroupId ?? 'none'}-${activeConvId}`}
              pid={pid}
              groupId={effectiveGroupId}
              conversationId={activeConvId}
            />
          </div>
        ) : (
          <ProjectSettingsPanel projectId={pid} />
        )}
      </div>
    </div>
  )

  return (
    <div className="flex h-full min-h-0">
      <div className="flex flex-col flex-1 min-h-0 min-w-0">
        {isMultiConv ? (
          <div className={cn(
            'flex-1 min-h-0 grid',
            displayConversations.length === 2 && 'grid-cols-2',
            displayConversations.length >= 3 && 'grid-cols-3',
          )}>
            {displayConversations.map((conv, idx) => (
              <div
                key={String(conv.id)}
                className={cn('min-h-0', idx < displayConversations.length - 1 && 'border-r')}
              >
                <ChatColumn
                  pid={pid}
                  conversationId={conv.id}
                  title={conv.title || conv.side || `Chat ${idx + 1}`}
                  showTitle
                  compact
                  onSettingsUpdated={() => {
                    refetchConvDetail()
                    queryClient.invalidateQueries({ queryKey: ['conversations', pid] })
                  }}
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="flex-1 min-h-0 relative">
            <ChatColumn
              key={String(activeConvId)}
              pid={pid}
              conversationId={activeConvId}
              title={activeConvDetail?.title}
              onSettingsUpdated={() => {
                refetchConvDetail()
                queryClient.invalidateQueries({ queryKey: ['conversations', pid] })
              }}
            />
          </div>
        )}

        {!settingsOpen && (
          <div className="absolute bottom-4 right-4 z-10">
            <button
              onClick={() => setSettingsOpen(true)}
              className="p-2 rounded-lg bg-background border shadow-sm hover:bg-accent text-muted-foreground"
              aria-label={t('project.settings')}
            >
              <PanelRightOpen className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      {settingsOpen && (
        <div className="w-80 shrink-0 hidden md:block">
          {settingsPanel}
        </div>
      )}
    </div>
  )
}
