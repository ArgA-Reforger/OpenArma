'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { toast } from 'sonner'
import { useApi } from '@/hooks/use-api'
import { useStreamStore } from '@/stores/stream-store'
import { cn } from '@/lib/utils'
import { useI18n } from '@/lib/i18n'
import {
  ArrowDown, ChevronDown, ChevronUp, ChevronLeft, ChevronRight, Copy, Edit, Bot,
  RefreshCw, Square, Workflow, CheckCircle2, Loader2, Crosshair, Globe,
  Gamepad2, Shield, Settings, Wrench, AlertCircle,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { NodeExecutionState, ToolCallEvent } from '@/stores/stream-store'
import { ConversationResourcePanel } from './conversation-settings'

export interface Message {
  id: number
  role: string
  content: string | null
  created_time: string
  parent_message_id?: number | null
  structured_data?: Record<string, unknown> | null
  metadata?: {
    agent_id?: number
    agent_name?: string
    role?: string
    is_final?: boolean
    source?: string
    type?: string
    request_id?: number
    priority?: string
    group_count?: number
    has_orders?: boolean
    order_count?: number
    sender?: string
  } | null
}

interface PageData<T> {
  items: T[]
  total: number
  page: number
  size: number
  total_pages: number
}

interface BranchInfo {
  total: number
  active_index: number
}

interface ConvDetailData {
  agent_id?: number | string | null
  topology_id?: number | string | null
  mission_objective?: Record<string, unknown> | null
  source?: string
  title?: string | null
}

export interface ChatColumnProps {
  pid: string
  conversationId: number | string
  title?: string | null
  showTitle?: boolean
  compact?: boolean
  onSettingsUpdated?: () => void
  readonly?: boolean
  externalMessages?: Message[]
  externalSource?: string | null
}

export function ChatColumn({ pid, conversationId, title, showTitle = false, compact = false, onSettingsUpdated, readonly = false, externalMessages, externalSource }: ChatColumnProps) {
  const convId = conversationId
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()

  const { data: convDetail, refetch: refetchConvDetail } = useQuery({
    queryKey: ['conv-detail', pid, convId],
    queryFn: () => api.get<ConvDetailData>(`/projects/${pid}/conversations/${convId}`),
    enabled: !!convId && !readonly,
    staleTime: 30_000,
  })

  const { data: agentsList } = useQuery({
    queryKey: ['agents-conv-settings'],
    queryFn: () => api.get<PageData<{ id: number; name: string; model_name?: string | null }>>('/agents'),
    staleTime: 30_000,
    enabled: !readonly,
  })
  const { data: topologiesList } = useQuery({
    queryKey: ['topologies-conv-settings'],
    queryFn: () => api.get<PageData<{ id: number; name: string }>>('/topologies'),
    staleTime: 30_000,
    enabled: !readonly,
  })

  const boundAgent = useMemo(() => {
    if (!convDetail?.agent_id || !agentsList?.items) return null
    return agentsList.items.find((a) => String(a.id) === String(convDetail.agent_id)) ?? null
  }, [convDetail?.agent_id, agentsList])

  const boundTopology = useMemo(() => {
    if (!convDetail?.topology_id || !topologiesList?.items) return null
    return topologiesList.items.find((t) => String(t.id) === String(convDetail.topology_id)) ?? null
  }, [convDetail?.topology_id, topologiesList])

  const [settingsExpanded, setSettingsExpanded] = useState(false)

  const [messages, setMessages] = useState<Message[]>(externalMessages || [])
  const [input, setInput] = useState('')
  const [editingMsg, setEditingMsg] = useState<Message | null>(null)
  const [editMsgValue, setEditMsgValue] = useState('')
  const [visibleTurnIdx, setVisibleTurnIdx] = useState(0)
  const [expandedAgents, setExpandedAgents] = useState<Set<number>>(new Set())
  const [expandedToolDetails, setExpandedToolDetails] = useState<Set<string>>(new Set())
  const [branchMap, setBranchMap] = useState<Record<string, BranchInfo>>({})
  const [viewingOldBranch, setViewingOldBranch] = useState<Message[] | null>(null)
  const [showNewContent, setShowNewContent] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const turnRefs = useRef<Map<number, HTMLDivElement>>(new Map())
  const isNearBottomRef = useRef(true)
  const userScrolledUpRef = useRef(false)
  const isInitialLoadRef = useRef(true)
  const skipScrollOnLoadRef = useRef(false)

  const streamState = useStreamStore((s) => s.streams[convId ?? -1])
  const startStream = useStreamStore((s) => s.startStream)
  const abortStream = useStreamStore((s) => s.abortStream)
  const clearStream = useStreamStore((s) => s.clearStream)

  const streaming = streamState?.streaming ?? false
  const streamContent = streamState?.streamContent ?? ''
  const multiAgentStream = streamState?.multiAgentStream ?? null
  const activeAgentName = streamState?.activeAgentName ?? null
  const dagNodeStates: NodeExecutionState[] = streamState?.dagNodeStates ?? []
  const streamToolCalls: ToolCallEvent[] = streamState?.toolCalls ?? []

  const turns = useMemo(() => {
    const result: { userMsg: Message; index: number }[] = []
    messages.forEach((msg, i) => {
      if (msg.role === 'user') result.push({ userMsg: msg, index: i })
    })
    return result
  }, [messages])

  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container || turns.length === 0) return

    function onScroll() {
      const containerRect = container!.getBoundingClientRect()
      const containerMid = containerRect.top + containerRect.height / 2
      let closest = 0
      let closestDist = Infinity
      turns.forEach((turn, idx) => {
        const el = turnRefs.current.get(turn.userMsg.id)
        if (!el) return
        const rect = el.getBoundingClientRect()
        const dist = Math.abs(rect.top - containerMid)
        if (dist < closestDist) {
          closestDist = dist
          closest = idx
        }
      })
      setVisibleTurnIdx(closest)
    }

    container.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => container.removeEventListener('scroll', onScroll)
  }, [turns])

  const editMsgMutation = useMutation({
    mutationFn: ({ msgId, content }: { msgId: number; content: string }) =>
      api.post<{ content: string }>(
        `/projects/${pid}/conversations/${convId}/messages/${msgId}/edit-and-resend`,
        { content },
      ),
    onSuccess: async (_, { content }) => {
      setEditingMsg(null)
      if (convId) {
        await loadMessages(convId)
        startStream({ pid, convId, content, resend: true })
      }
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const currentPageRef = useRef<number>(1)
  const loadingOlderRef = useRef(false)
  const [hasOlder, setHasOlder] = useState(false)

  const loadMessages = useCallback(
    async (cid: number | string) => {
      isInitialLoadRef.current = true
      try {
        const [firstPage, branchData] = await Promise.all([
          api.get<PageData<Message>>(
            `/projects/${pid}/conversations/${cid}/messages?size=100`,
          ),
          api.get<{ branches: Record<string, BranchInfo> }>(
            `/projects/${pid}/conversations/${cid}/branches`,
          ).catch(() => ({ branches: {} })),
        ])
        const tp = firstPage.total_pages || 1
        if (tp <= 1) {
          currentPageRef.current = 1
          setHasOlder(false)
          setMessages(firstPage.items || [])
        } else {
          const lastPageData = await api.get<PageData<Message>>(
            `/projects/${pid}/conversations/${cid}/messages?size=100&page=${tp}`,
          )
          currentPageRef.current = tp
          setHasOlder(tp > 1)
          setMessages(lastPageData.items || [])
        }
        setBranchMap(branchData.branches || {})
      } catch {
        setMessages([])
        setBranchMap({})
      }
    },
    [api, pid],
  )

  const lastMsgIdRef = useRef<number | string | null>(null)
  useEffect(() => {
    lastMsgIdRef.current = messages.length > 0 ? messages[messages.length - 1].id : null
  }, [messages])

  const pollNewMessages = useCallback(
    async (cid: number | string) => {
      try {
        const lastId = lastMsgIdRef.current
        if (!lastId) return
        const data = await api.get<PageData<Message>>(
          `/projects/${pid}/conversations/${cid}/messages?size=100&after=${lastId}`,
        )
        const newItems = data.items || []
        if (newItems.length > 0) {
          setMessages(prev => [...prev, ...newItems])
        }
      } catch { /* silent */ }
    },
    [api, pid],
  )

  const loadOlderMessages = useCallback(
    async (cid: number | string) => {
      if (loadingOlderRef.current || currentPageRef.current <= 1) return
      loadingOlderRef.current = true
      try {
        const prevPage = currentPageRef.current - 1
        const data = await api.get<PageData<Message>>(
          `/projects/${pid}/conversations/${cid}/messages?size=100&page=${prevPage}`,
        )
        const olderItems = data.items || []
        if (olderItems.length > 0) {
          currentPageRef.current = prevPage
          setHasOlder(prevPage > 1)
          const container = scrollContainerRef.current
          const prevHeight = container?.scrollHeight ?? 0
          setMessages(prev => [...olderItems, ...prev])
          requestAnimationFrame(() => {
            if (container) {
              container.scrollTop = container.scrollHeight - prevHeight
            }
          })
        } else {
          setHasOlder(false)
        }
      } catch { /* silent */ }
      loadingOlderRef.current = false
    },
    [api, pid],
  )

  useEffect(() => {
    if (readonly) return
    if (convId) {
      loadMessages(convId)
    } else {
      setMessages([])
    }
  }, [convId, loadMessages, readonly])

  useEffect(() => {
    if (readonly || !convId) return
    const convs = queryClient.getQueryData<PageData<{ id: number; source?: string }>>(['conversations', pid])
    const conv = convs?.items?.find((c) => String(c.id) === String(convId))
    if (conv?.source !== 'arma') return
    const timer = setInterval(() => {
      pollNewMessages(convId)
    }, 10_000)
    return () => clearInterval(timer)
  }, [convId, queryClient, pid, pollNewMessages, readonly])

  useEffect(() => {
    if (readonly || !convId || !streamState) return
    const { completedMessages, streaming: isStreaming } = streamState
    if (!isStreaming && completedMessages && completedMessages.length > 0) {
      clearStream(convId)
      setViewingOldBranch(null)
      pollNewMessages(convId)
      queryClient.invalidateQueries({ queryKey: ['conversations', pid] })
    }
  }, [convId, streamState, clearStream, pollNewMessages, queryClient, pid])

  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container) return

    function onScroll() {
      if (!container) return
      const threshold = 80
      const distFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight
      const nearBottom = distFromBottom < threshold
      isNearBottomRef.current = nearBottom
      if (nearBottom) {
        userScrolledUpRef.current = false
        setShowNewContent(false)
      } else {
        userScrolledUpRef.current = true
      }
      if (container.scrollTop < 100 && hasOlder && convId) {
        loadOlderMessages(convId)
      }
    }

    container.addEventListener('scroll', onScroll, { passive: true })
    return () => container.removeEventListener('scroll', onScroll)
  }, [streaming, convId, hasOlder, loadOlderMessages])

  useEffect(() => {
    if (viewingOldBranch) return
    if (isInitialLoadRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'instant' as ScrollBehavior })
      isInitialLoadRef.current = false
      isNearBottomRef.current = true
      userScrolledUpRef.current = false
    } else if (userScrolledUpRef.current) {
      setShowNewContent(true)
    } else if (isNearBottomRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'instant' as ScrollBehavior })
    }
  }, [messages, streamContent, multiAgentStream, streaming, viewingOldBranch])

  function scrollToBottom() {
    userScrolledUpRef.current = false
    isNearBottomRef.current = true
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    setShowNewContent(false)
  }

  const DEFAULT_TITLES = ['新对话', 'New Chat', '未命名对话', 'Untitled']

  function conversationNeedsTitle(): boolean {
    const convs = queryClient.getQueryData<PageData<{ id: number; title: string | null }>>(['conversations', pid])
    if (!convs) return true
    const conv = convs.items.find((c) => c.id === convId)
    if (!conv) return true
    return !conv.title || DEFAULT_TITLES.includes(conv.title)
  }

  const handleTitleGenerated = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['conversations', pid] })
  }, [queryClient, pid])

  async function handleSend() {
    if (!input.trim() || !convId || streaming) return

    if (!convDetail?.agent_id && !convDetail?.topology_id) {
      toast.error(t('chat.noAgentBound'))
      return
    }

    const userContent = input.trim()
    const needsTitle = conversationNeedsTitle()

    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: userContent,
      created_time: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    startStream({
      pid,
      convId,
      content: userContent,
      resend: false,
      needsTitle,
      onTitleGenerated: handleTitleGenerated,
    })
  }

  async function handleSwitchBranch(userMsgId: number, direction: 'prev' | 'next') {
    if (!convId) return
    skipScrollOnLoadRef.current = true
    isNearBottomRef.current = false

    const bi = branchMap[String(userMsgId)]
    if (!bi || bi.total <= 1) return

    const newIdx = direction === 'prev'
      ? Math.max(0, bi.active_index - 1)
      : Math.min(bi.total - 1, bi.active_index + 1)

    if (newIdx === bi.active_index) return

    if (streaming) {
      const isLatestBranch = newIdx === bi.total - 1

      if (isLatestBranch) {
        setViewingOldBranch(null)
      } else {
        try {
          const data = await api.get<{
            branches: { id: number; is_active: boolean; messages: { id: number; role: string; content: string | null; created_time: string; metadata?: Record<string, unknown> }[] }[]
          }>(`/projects/${pid}/conversations/${convId}/messages/${userMsgId}/branches`)

          const target = data.branches[newIdx]
          if (target) {
            const branchMsgs: Message[] = target.messages
              .slice()
              .sort((a, b) => {
                const aFinal = a.metadata?.is_final ? 1 : 0
                const bFinal = b.metadata?.is_final ? 1 : 0
                if (aFinal !== bFinal) return aFinal - bFinal
                return a.id - b.id
              })
              .map((m) => ({
                id: m.id,
                role: m.role,
                content: m.content,
                created_time: m.created_time,
                metadata: m.metadata as Message['metadata'],
              }))
            setViewingOldBranch([...messages, ...branchMsgs])
          }
        } catch {
          toast.error(t('chat.switchBranchFailed'))
          return
        }
      }

      setBranchMap((prev) => ({
        ...prev,
        [String(userMsgId)]: { ...prev[String(userMsgId)], active_index: newIdx },
      }))
      return
    }

    try {
      const data = await api.get<{
        branches: { id: number; messages: { id: number }[] }[]
        active_index: number
      }>(`/projects/${pid}/conversations/${convId}/messages/${userMsgId}/branches`)

      const targetBranch = data.branches[newIdx]
      if (!targetBranch) return
      const targetId = targetBranch.messages[0]?.id ?? targetBranch.id

      await api.post(
        `/projects/${pid}/conversations/${convId}/messages/${userMsgId}/switch-branch`,
        { target_branch_id: targetId },
      )

      setViewingOldBranch(null)
      await loadMessages(convId)
    } catch {
      toast.error(t('chat.switchBranchFailed'))
    }
  }

  function handleRegenerate() {
    if (!convId || streaming) return
    const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user')
    if (!lastUserMsg?.content) return

    const lastUserIdx = messages.lastIndexOf(lastUserMsg)
    setMessages((prev) => prev.slice(0, lastUserIdx + 1))

    const uid = String(lastUserMsg.id)
    const prev = branchMap[uid]
    setBranchMap((m) => ({
      ...m,
      [uid]: { total: (prev?.total ?? 1) + 1, active_index: prev ? prev.total : 1 },
    }))

    startStream({ pid, convId, content: lastUserMsg.content, resend: true })
  }

  function handleStopGeneration() {
    if (convId) abortStream(convId)
  }

  function handleCopyMessage(content: string | null) {
    if (!content) return
    navigator.clipboard.writeText(content)
    toast.success(t('chat.messageCopied'))
  }

  function scrollToTurn(turnIdx: number) {
    const turn = turns[turnIdx]
    if (!turn) return
    const el = turnRefs.current.get(turn.userMsg.id)
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function toggleAgentExpand(agentId: number) {
    setExpandedAgents((prev) => {
      const next = new Set(prev)
      if (next.has(agentId)) next.delete(agentId)
      else next.add(agentId)
      return next
    })
  }

  const displayMessages = viewingOldBranch ?? messages
  const isViewingOld = viewingOldBranch !== null

  const lastAssistantIdx = useMemo(() => {
    for (let i = displayMessages.length - 1; i >= 0; i--) {
      if (displayMessages[i].role === 'assistant') return i
    }
    return -1
  }, [displayMessages])

  const groupNameMap = useMemo(() => {
    const map = new Map<string, string>()
    for (const msg of messages) {
      if (msg.metadata?.type !== 'situation_report' || !msg.content) continue
      const re = /\[Squad (\d+):\s*([^\]]+)\].*?\(.*?id:\s*([^)]+)\)/g
      let m
      while ((m = re.exec(msg.content))) {
        const squadNum = m[1]
        const label = m[2].trim()
        const groupId = m[3].trim()
        const displayName = label.startsWith('#') ? `Squad ${squadNum}` : label
        map.set(groupId, displayName)
      }
    }
    return map
  }, [messages])

  const isAgentMessage = (msg: Message) => msg.metadata?.role === 'agent'
  const isFinalMessage = (msg: Message) => msg.metadata?.is_final === true
  const isSituationReport = (msg: Message) => msg.metadata?.type === 'situation_report'
  const isTacticalResponse = (msg: Message) => msg.metadata?.type === 'tactical_response'
  const getSourceLabel = (msg: Message) => {
    const src = msg.metadata?.source
    if (src === 'arma_mod') return 'Arma'
    if (src === 'arma_chat') return 'Game'
    if (src === 'web') return 'Web'
    return null
  }

  const isArmaConv = readonly ? externalSource === 'arma' : convDetail?.source === 'arma'
  const displayTitle = title || convDetail?.title || t('chat.untitled')

  const handleSettingsUpdated = useCallback(() => {
    refetchConvDetail()
    queryClient.invalidateQueries({ queryKey: ['conversations', pid] })
    onSettingsUpdated?.()
  }, [refetchConvDetail, queryClient, pid, onSettingsUpdated])

  return (
    <div className="flex flex-col h-full min-h-0 relative">
      <div className="shrink-0 border-b bg-muted/30">
        <div className="flex items-center justify-between px-3 py-1.5 gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-sm font-medium truncate">{displayTitle}</span>
            {boundAgent ? (
              <span className="text-[10px] text-muted-foreground truncate">
                {boundAgent.name}{boundAgent.model_name ? ` · ${boundAgent.model_name}` : ''}
              </span>
            ) : boundTopology ? (
              <span className="text-[10px] text-muted-foreground truncate">
                <Workflow className="inline h-2.5 w-2.5 mr-0.5" />{boundTopology.name}
              </span>
            ) : convDetail && !convDetail.agent_id && !convDetail.topology_id ? (
              <span className="text-[10px] text-orange-500 shrink-0">{t('chat.noAgentHint')}</span>
            ) : null}
          </div>
          {!readonly && (
            <button
              onClick={() => setSettingsExpanded(!settingsExpanded)}
              className="p-1 rounded-md hover:bg-accent text-muted-foreground transition-colors shrink-0"
              title={t('chat.subConvSettings')}
            >
              {settingsExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <Settings className="h-3.5 w-3.5" />}
            </button>
          )}
        </div>
        {!readonly && settingsExpanded && convDetail && (
          <div className="border-t max-h-[50vh] overflow-y-auto scrollbar-thin">
            <div className="px-3 pb-2">
              <ConversationResourcePanel
                projectId={pid}
                conversationId={convId}
                agentId={convDetail.agent_id}
                topologyId={convDetail.topology_id}
                missionObjective={convDetail.mission_objective}
                isArma={isArmaConv}
                onUpdated={handleSettingsUpdated}
              />
            </div>
          </div>
        )}
      </div>

      <div ref={scrollContainerRef} className={cn('flex-1 overflow-y-auto min-h-0 scrollbar-thin', compact ? 'p-2' : 'p-4')}>
        <div className={cn('space-y-4', !compact && 'max-w-3xl mx-auto')}>
          {hasOlder && (
            <div className="flex justify-center py-2">
              <button
                onClick={() => convId && loadOlderMessages(convId)}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                {t('chat.loadOlder')}
              </button>
            </div>
          )}
          {displayMessages.map((msg, msgIdx) => {
            const isEditing = editingMsg?.id === msg.id
            const isUserTurn = msg.role === 'user'
            const isAgent = isAgentMessage(msg)
            const isFinal = isFinalMessage(msg)
            const isLastAssistant = msgIdx === lastAssistantIdx

            let msgTime = ''
            if (msg.created_time) {
              const cur = new Date(msg.created_time)
              const now = new Date()
              const isToday = cur.toDateString() === now.toDateString()
              const yesterday = new Date(now)
              yesterday.setDate(yesterday.getDate() - 1)
              const isYesterday = cur.toDateString() === yesterday.toDateString()
              const time = cur.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              if (isToday) msgTime = time
              else if (isYesterday) msgTime = `${t('chat.yesterday')} ${time}`
              else msgTime = `${cur.toLocaleDateString([], { month: 'short', day: 'numeric' })} ${time}`
            }

            let branchNav: { userMsgId: number; info: BranchInfo } | null = null
            if (isUserTurn) {
              const bi = branchMap[String(msg.id)]
              if (bi && bi.total > 1) {
                branchNav = { userMsgId: msg.id, info: bi }
              } else if (streaming && msg === messages.filter((m) => m.role === 'user').at(-1)) {
                const existingBi = branchMap[String(msg.id)]
                if (existingBi) {
                  branchNav = { userMsgId: msg.id, info: { total: existingBi.total + 1, active_index: existingBi.total } }
                }
              }
            }

            const msgMeta = (
              <div className="shrink-0 self-stretch flex flex-col justify-between items-end w-[100px]">
                <span className="text-[10px] text-muted-foreground/50 select-none">{msgTime}</span>
                <div className="flex items-center gap-0.5 self-start invisible group-hover:visible">
                  <button onClick={() => handleCopyMessage(msg.content)} className="p-1 rounded hover:bg-accent text-muted-foreground"><Copy className="h-3.5 w-3.5" /></button>
                </div>
              </div>
            )

            if (isSituationReport(msg)) {
              const reqId = msg.metadata?.request_id ?? '?'
              const groupCount = msg.metadata?.group_count ?? 0
              const prio = msg.metadata?.priority
              const [sitExpanded, setSitExpanded] = [
                expandedAgents.has(msg.id),
                (v: boolean) => setExpandedAgents(prev => { const s = new Set(prev); v ? s.add(msg.id) : s.delete(msg.id); return s })
              ]

              return (
                <div key={msg.id}>
                  <div className="group flex items-start gap-1">
                  <div className="flex-1 min-w-0">
                  <button
                    onClick={() => setSitExpanded(!sitExpanded)}
                    className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors py-1 w-full"
                  >
                    {sitExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                    <Crosshair className="h-3 w-3 text-amber-500" />
                    <span>{t('armaChat.situationReport')} #{String(reqId)}</span>
                    <Badge variant="outline" className="text-[10px] px-1 py-0">{groupCount} {t('armaChat.squads')}</Badge>
                    {prio === 'critical' && <Badge variant="destructive" className="text-[10px] px-1 py-0">{t('armaChat.urgent')}</Badge>}
                  </button>
                  {sitExpanded && (
                    <div className="ml-5 mt-1 rounded-lg px-3 py-2 text-xs bg-amber-500/5 border border-amber-500/20 whitespace-pre-wrap font-mono max-h-[300px] overflow-y-auto">
                      {msg.content}
                    </div>
                  )}
                  </div>
                  <div className="shrink-0 self-stretch flex flex-col justify-between items-end w-[100px]">
                    <span className="text-[10px] text-muted-foreground/50 select-none">{msgTime}</span>
                    {sitExpanded && (
                      <div className="flex items-center gap-0.5 self-start invisible group-hover:visible">
                        <button onClick={() => handleCopyMessage(msg.content)} className="p-1 rounded hover:bg-accent text-muted-foreground"><Copy className="h-3.5 w-3.5" /></button>
                      </div>
                    )}
                  </div>
                  </div>
                </div>
              )
            }

            if (isTacticalResponse(msg)) {
              const orders = (msg.structured_data as { orders?: { type: string; group_id: string; target?: number[]; waypoints?: { pos: number[] }[] }[] })?.orders ?? []
              const briefing = (msg.structured_data as { briefing?: string })?.briefing ?? ''
              const historyToolCalls = (msg.structured_data as { tool_calls?: { tool_name: string; tool_type: string; display_name?: string; arguments: Record<string, unknown>; result?: string; duration_ms?: number; status: string }[] })?.tool_calls ?? []
              const sourceLabel = getSourceLabel(msg)
              const tcListKey = msg.id + 100000
              const [tcExpanded, setTcExpanded] = [
                expandedAgents.has(tcListKey),
                (v: boolean) => setExpandedAgents(prev => { const s = new Set(prev); v ? s.add(tcListKey) : s.delete(tcListKey); return s })
              ]

              return (
                <div key={msg.id}>
                  <div className="group flex items-start gap-1">
                  <div className="flex-1 min-w-0">
                  {sourceLabel && (
                    <div className="flex items-center gap-1 mb-1">
                      <Shield className="h-3 w-3 text-green-500" />
                      <span className="text-[10px] font-medium text-green-600 dark:text-green-400">{t('armaChat.tacticalResponse')}</span>
                    </div>
                  )}
                  <div>
                      {historyToolCalls.length > 0 && (
                        <div className="mb-2">
                          <button
                            onClick={() => setTcExpanded(!tcExpanded)}
                            className="flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground transition-colors py-0.5"
                          >
                            {tcExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                            <Wrench className="h-3 w-3" />
                            <span>{historyToolCalls.length} {t('armaChat.toolCallPlural')}</span>
                            {!tcExpanded && (
                              <span className="text-muted-foreground/60">
                                ({historyToolCalls.map(tc => tc.display_name || (() => { const k = `builtinTool.tool_${tc.tool_name}`; const v = t(k); return v !== k ? v : tc.tool_name })()).join(', ')})
                              </span>
                            )}
                          </button>
                          {tcExpanded && (
                            <div className="ml-4 mt-1 space-y-1">
                              {historyToolCalls.map((tc, i) => {
                                const detailKey = `${msg.id}-tc-${i}`
                                const isDetailOpen = expandedToolDetails.has(detailKey)
                                const toggleDetail = (e: React.MouseEvent) => {
                                  e.stopPropagation()
                                  setExpandedToolDetails(prev => {
                                    const s = new Set(prev)
                                    if (s.has(detailKey)) s.delete(detailKey); else s.add(detailKey)
                                    return s
                                  })
                                }
                                const resolvedName = tc.display_name || (() => { const k = `builtinTool.tool_${tc.tool_name}`; const v = t(k); return v !== k ? v : tc.tool_name })()
                                return (
                                  <div key={i} className="rounded bg-muted/40 border border-border/30 overflow-hidden">
                                    <button onClick={toggleDetail} className="flex items-center gap-2 text-[11px] px-2.5 py-1.5 w-full hover:bg-muted/60 transition-colors">
                                      {tc.status === 'error' ? (
                                        <AlertCircle className="h-3 w-3 text-destructive shrink-0" />
                                      ) : (
                                        <CheckCircle2 className="h-3 w-3 text-green-500 shrink-0" />
                                      )}
                                      <span className="font-medium">{resolvedName}</span>
                                      {resolvedName !== tc.tool_name && <span className="text-muted-foreground/40 font-mono text-[10px]">{tc.tool_name}</span>}
                                      {tc.duration_ms != null && (
                                        <span className="text-muted-foreground/40 text-[10px]">{tc.duration_ms}ms</span>
                                      )}
                                      {isDetailOpen ? <ChevronUp className="h-3 w-3 ml-auto text-muted-foreground" /> : <ChevronDown className="h-3 w-3 ml-auto text-muted-foreground" />}
                                    </button>
                                    {isDetailOpen && (
                                      <div className="px-2.5 pb-2 space-y-1.5 border-t border-border/20">
                                        {Object.keys(tc.arguments || {}).length > 0 && (
                                          <div className="pt-1.5">
                                            <div className="text-[10px] font-medium text-muted-foreground mb-0.5">{t('armaChat.toolParams')}</div>
                                            <pre className="text-[11px] font-mono bg-background/50 rounded px-2 py-1 overflow-x-auto max-h-[120px]">{JSON.stringify(tc.arguments, null, 2)}</pre>
                                          </div>
                                        )}
                                        {tc.result && (
                                          <div>
                                            <div className="text-[10px] font-medium text-muted-foreground mb-0.5">{t('armaChat.toolResult')}</div>
                                            <pre className="text-[11px] font-mono bg-background/50 rounded px-2 py-1 overflow-x-auto max-h-[150px] whitespace-pre-wrap">{tc.result}</pre>
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      )}
                      {briefing && (
                        <div className="rounded-lg px-4 py-2 text-sm bg-muted whitespace-pre-wrap mb-2">{briefing}</div>
                      )}
                      {orders.length > 0 && (
                        <div className="rounded-lg border border-green-500/20 bg-green-500/5 px-3 py-2 text-xs space-y-1">
                          <div className="font-medium text-green-600 dark:text-green-400">{t('armaChat.orders')} ({orders.length})</div>
                          {orders.map((o, i) => (
                            <div key={i} className="flex flex-wrap items-center gap-2 text-muted-foreground">
                              <Badge variant="outline" className="text-[10px] px-1 py-0 uppercase">{o.type}</Badge>
                              <span className="font-mono text-[11px]">{groupNameMap.get(o.group_id ?? '') || o.group_id?.replace(/\s*\{\}$/, '').slice(-4)}</span>
                              {o.target && <span className="font-mono text-[11px]">[{o.target.map(n => Math.round(n)).join(', ')}]</span>}
                              {o.waypoints && o.waypoints.length > 0 && (
                                <span className="font-mono text-[11px]">
                                  {o.waypoints.map((wp) => `[${wp.pos.map(n => Math.round(n)).join(',')}]`).join(' → ')}
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      {!briefing && !orders.length && msg.content && (
                        <div className="rounded-lg px-4 py-2 text-sm bg-muted whitespace-pre-wrap">{msg.content}</div>
                      )}
                  </div>
                  </div>
                  <div className="shrink-0 self-stretch flex flex-col justify-between items-end w-[100px]">
                    <span className="text-[10px] text-muted-foreground/50 select-none">{msgTime}</span>
                    <div className="flex items-center gap-0.5 self-start invisible group-hover:visible">
                      <button onClick={() => handleCopyMessage(briefing || msg.content)} className="p-1 rounded hover:bg-accent text-muted-foreground"><Copy className="h-3.5 w-3.5" /></button>
                    </div>
                  </div>
                  </div>
                </div>
              )
            }

            if (isAgent) {
              const agentId = msg.metadata!.agent_id!
              const agentName = msg.metadata!.agent_name || 'Agent'
              const isExpanded = expandedAgents.has(agentId)

              return (
                <div key={msg.id}>
                  <div className="group flex items-start gap-1">
                  <div className="flex-1 min-w-0">
                  <button
                    onClick={() => toggleAgentExpand(agentId)}
                    className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors py-1"
                  >
                    {isExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                    <Bot className="h-3.5 w-3.5" />
                    <span className="font-medium">{agentName}</span>
                  </button>
                  {isExpanded && (
                    <div className="ml-6 mt-1 rounded-lg px-4 py-2 text-sm bg-muted/50 border border-border/50 whitespace-pre-wrap">
                      {msg.content}
                    </div>
                  )}
                  </div>
                  {msgMeta}
                  </div>
                </div>
              )
            }

            if (isFinal) {
              const roleLabel = msg.metadata?.role === 'coordinator'
                ? t('chat.coordinatorSummary')
                : t('chat.aggregatorSummary')

              return (
                <div key={msg.id}>
                  <div className="group flex items-start gap-1">
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-muted-foreground mb-1 font-medium">{roleLabel}</div>
                    <div className="rounded-lg px-4 py-2 text-sm bg-muted whitespace-pre-wrap">
                      {msg.content}
                    </div>
                  </div>
                  <div className="shrink-0 self-stretch flex flex-col justify-between items-end w-[100px]">
                    <span className="text-[10px] text-muted-foreground/50 select-none">{msgTime}</span>
                    <div className="flex items-center gap-0.5 self-start invisible group-hover:visible">
                      <button
                        onClick={() => handleCopyMessage(msg.content)}
                        className="p-1 rounded hover:bg-accent text-muted-foreground"
                        aria-label={t('chat.copyMessage')}
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </button>
                      {!readonly && isLastAssistant && !streaming && (
                        <button
                          onClick={handleRegenerate}
                          className="p-1 rounded hover:bg-accent text-muted-foreground"
                          aria-label={t('chat.regenerate')}
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                  </div>
                </div>
              )
            }

            return (
              <div key={msg.id}>
                <div className="group flex items-start gap-1">
                <div
                  ref={(el) => {
                    if (isUserTurn && el) {
                      turnRefs.current.set(msg.id, el)
                    }
                  }}
                  data-turn-id={isUserTurn ? msg.id : undefined}
                  className={cn('flex-1 min-w-0', msg.role === 'user' && 'text-right')}
                >
                  {isEditing ? (
                    <div className="max-w-[80%] w-full space-y-2 ml-auto">
                      <textarea
                        value={editMsgValue}
                        onChange={(e) => setEditMsgValue(e.target.value)}
                        className="w-full min-h-[60px] rounded-lg border border-primary px-4 py-2 text-sm bg-primary/5 focus:outline-none focus:ring-1 focus:ring-primary resize-none text-left"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Escape') setEditingMsg(null)
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault()
                            if (editMsgValue.trim()) {
                              editMsgMutation.mutate({ msgId: msg.id, content: editMsgValue.trim() })
                            }
                          }
                        }}
                      />
                      <div className="flex gap-1 justify-end">
                        <Button size="sm" variant="ghost" onClick={() => setEditingMsg(null)}>
                          {t('common.cancel')}
                        </Button>
                        <Button
                          size="sm"
                          disabled={editMsgMutation.isPending || !editMsgValue.trim()}
                          onClick={() => editMsgMutation.mutate({ msgId: msg.id, content: editMsgValue.trim() })}
                        >
                          {editMsgMutation.isPending ? t('common.saving') : t('common.save')}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <>
                      {isUserTurn && msg.metadata?.source === 'arma_chat' && (
                        <div className="flex items-center gap-1 mb-1 justify-end">
                          <Gamepad2 className="h-3 w-3 text-amber-500" />
                          <span className="text-[10px] text-amber-600 dark:text-amber-400">{msg.metadata?.sender || 'Game'}</span>
                        </div>
                      )}
                      {isUserTurn && msg.metadata?.source === 'web' && msg.metadata?.type !== undefined && (
                        <div className="flex items-center gap-1 mb-1 justify-end">
                          <Globe className="h-3 w-3 text-blue-500" />
                          <span className="text-[10px] text-blue-600 dark:text-blue-400">Web</span>
                          {msg.metadata?.priority === 'critical' && (
                            <Badge variant="destructive" className="text-[10px] px-1 py-0">{t('armaChat.urgent')}</Badge>
                          )}
                        </div>
                      )}
                      <div
                        className={cn(
                          'rounded-lg px-4 py-2 text-sm whitespace-pre-wrap text-left inline-block',
                          msg.role === 'user'
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted',
                        )}
                      >
                        {msg.content}
                      </div>
                    </>
                  )}
                </div>
                <div className="shrink-0 self-stretch flex flex-col justify-between items-end w-[100px]">
                  <span className="text-[10px] text-muted-foreground/50 select-none">{msgTime}</span>
                  <div className="flex items-center gap-0.5 self-start invisible group-hover:visible">
                    <button
                      onClick={() => handleCopyMessage(msg.content)}
                      className="p-1 rounded hover:bg-accent text-muted-foreground"
                      aria-label={t('chat.copyMessage')}
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </button>
                    {!readonly && msg.role === 'user' && (
                      <button
                        onClick={() => { setEditingMsg(msg); setEditMsgValue(msg.content || '') }}
                        className="p-1 rounded hover:bg-accent text-muted-foreground"
                        aria-label={t('chat.editMessage')}
                      >
                        <Edit className="h-3.5 w-3.5" />
                      </button>
                    )}
                    {!readonly && isLastAssistant && !streaming && msg.role === 'assistant' && (
                      <button
                        onClick={handleRegenerate}
                        className="p-1 rounded hover:bg-accent text-muted-foreground"
                        aria-label={t('chat.regenerate')}
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                </div>
                </div>
                {!readonly && branchNav && (
                  <div className={cn(
                    'flex items-center gap-1 text-xs text-muted-foreground mt-1',
                    isUserTurn ? 'justify-end' : '',
                  )}>
                    <button
                      onClick={() => handleSwitchBranch(branchNav!.userMsgId, 'prev')}
                      disabled={branchNav.info.active_index === 0}
                      className="p-0.5 rounded hover:bg-accent disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="h-3.5 w-3.5" />
                    </button>
                    <span className="tabular-nums">
                      {t('chat.branchOf', { current: String(branchNav.info.active_index + 1), total: String(branchNav.info.total) })}
                    </span>
                    <button
                      onClick={() => handleSwitchBranch(branchNav!.userMsgId, 'next')}
                      disabled={branchNav.info.active_index === branchNav.info.total - 1}
                      className="p-0.5 rounded hover:bg-accent disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <ChevronRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )}
              </div>
            )
          })}

          {/* Arma AI processing indicator */}
          {!streaming && !isViewingOld && displayMessages.length > 0 && (() => {
            const lastMsg = displayMessages[displayMessages.length - 1]
            const isArmaPending = lastMsg?.metadata?.type === 'situation_report' && lastMsg?.role === 'user'
            if (!isArmaPending) return null
            const reqId = lastMsg.metadata?.request_id ?? '?'
            return (
              <div className="flex items-center gap-2 py-2 px-3 rounded-lg bg-amber-500/5 border border-amber-500/20 animate-pulse">
                <Loader2 className="h-4 w-4 animate-spin text-amber-500" />
                <span className="text-sm text-amber-600 dark:text-amber-400">
                  {t('armaChat.aiProcessing')} (#{String(reqId)})
                </span>
              </div>
            )
          })()}

          {/* DAG execution status */}
          {streaming && !isViewingOld && dagNodeStates.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap py-2 px-3 rounded-lg bg-muted/30 border border-border/50">
              <Workflow className="h-4 w-4 text-muted-foreground shrink-0" />
              {dagNodeStates.map((ns) => (
                <div key={ns.nodeId} className="flex items-center gap-1 text-xs">
                  {ns.status === 'running' ? (
                    <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
                  ) : (
                    <CheckCircle2 className="h-3 w-3 text-green-500" />
                  )}
                  <span className={ns.status === 'running' ? 'text-foreground font-medium' : 'text-muted-foreground'}>
                    {ns.agentName || ns.nodeType}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Tool calls during streaming */}
          {streaming && !isViewingOld && streamToolCalls.length > 0 && (
            <div className="space-y-1.5 py-1">
              {streamToolCalls.map((tc, i) => {
                const tcStreamKey = `stream-tc-${i}`
                const isExpanded = expandedToolDetails.has(tcStreamKey)
                const toggleExpand = () => setExpandedToolDetails(prev => {
                  const s = new Set(prev)
                  if (s.has(tcStreamKey)) s.delete(tcStreamKey); else s.add(tcStreamKey)
                  return s
                })
                return (
                  <div key={i} className="rounded-md bg-muted/40 border border-border/30 overflow-hidden">
                    <button onClick={toggleExpand} className="flex items-center gap-2 text-xs px-3 py-1.5 w-full hover:bg-muted/60 transition-colors">
                      {tc.status === 'calling' ? (
                        <Loader2 className="h-3 w-3 animate-spin text-blue-500 shrink-0" />
                      ) : tc.status === 'error' ? (
                        <AlertCircle className="h-3 w-3 text-destructive shrink-0" />
                      ) : (
                        <CheckCircle2 className="h-3 w-3 text-green-500 shrink-0" />
                      )}
                      <Wrench className="h-3 w-3 text-muted-foreground shrink-0" />
                      <span className="font-medium text-foreground">{tc.displayName || (() => { const k = `builtinTool.tool_${tc.toolName}`; const v = t(k); return v !== k ? v : tc.toolName })()}</span>
                      {(tc.displayName || (() => { const k = `builtinTool.tool_${tc.toolName}`; return t(k) !== k })()) && <span className="text-muted-foreground/40 font-mono text-[10px]">{tc.toolName}</span>}
                      {tc.status === 'calling' && (
                        <span className="text-blue-500 ml-auto shrink-0">{t('armaChat.toolCalling')}</span>
                      )}
                      {isExpanded ? <ChevronUp className="h-3 w-3 ml-auto text-muted-foreground" /> : <ChevronDown className="h-3 w-3 ml-auto text-muted-foreground" />}
                    </button>
                    {isExpanded && (
                      <div className="px-3 pb-2 space-y-1.5 border-t border-border/20">
                        {Object.keys(tc.arguments).length > 0 && (
                          <div className="pt-1.5">
                            <div className="text-[10px] font-medium text-muted-foreground mb-0.5">{t('armaChat.toolParams')}</div>
                            <pre className="text-[11px] font-mono bg-background/50 rounded px-2 py-1 overflow-x-auto max-h-[120px]">{JSON.stringify(tc.arguments, null, 2)}</pre>
                          </div>
                        )}
                        {tc.result && (
                          <div>
                            <div className="text-[10px] font-medium text-muted-foreground mb-0.5">{t('armaChat.toolResult')}</div>
                            <pre className="text-[11px] font-mono bg-background/50 rounded px-2 py-1 overflow-x-auto max-h-[150px] whitespace-pre-wrap">{tc.result}</pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* Single-agent streaming */}
          {streaming && !isViewingOld && streamContent && !multiAgentStream && (
            <div className="flex items-start">
              <div className="max-w-[80%] rounded-lg px-4 py-2 text-sm bg-muted whitespace-pre-wrap">
                {streamContent}
                <span className="animate-pulse">▊</span>
              </div>
            </div>
          )}

          {/* Multi-agent streaming */}
          {streaming && !isViewingOld && multiAgentStream && (
            <div className="space-y-3">
              {activeAgentName && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
                  <Bot className="h-4 w-4" />
                  <span>{activeAgentName}...</span>
                </div>
              )}

              {multiAgentStream.agents.map((agent) => (
                <div key={agent.agentId}>
                  <button
                    onClick={() => toggleAgentExpand(agent.agentId)}
                    className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors py-1"
                  >
                    {expandedAgents.has(agent.agentId)
                      ? <ChevronDown className="h-3.5 w-3.5" />
                      : <ChevronRight className="h-3.5 w-3.5" />}
                    <Bot className="h-3.5 w-3.5" />
                    <span className="font-medium">{agent.agentName}</span>
                    {agent.content && <span className="text-xs opacity-60">({agent.content.length} chars)</span>}
                  </button>
                  {expandedAgents.has(agent.agentId) && agent.content && (
                    <div className="ml-6 mt-1 rounded-lg px-4 py-2 text-sm bg-muted/50 border border-border/50 whitespace-pre-wrap">
                      {agent.content}
                    </div>
                  )}
                </div>
              ))}

              {multiAgentStream.finalContent && (
                <div className="flex items-start">
                  <div className="max-w-[80%]">
                    <div className="text-xs text-muted-foreground mb-1 font-medium">
                      {multiAgentStream.finalRole === 'coordinator'
                        ? t('chat.coordinatorSummary')
                        : t('chat.aggregatorSummary')}
                    </div>
                    <div className="rounded-lg px-4 py-2 text-sm bg-muted whitespace-pre-wrap">
                      {multiAgentStream.finalContent}
                      <span className="animate-pulse">▊</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {!compact && turns.length > 1 && (
        <TooltipProvider delayDuration={200}>
          <div className="absolute right-6 top-1/2 -translate-y-1/2 flex flex-col items-center gap-1.5 z-10">
            {turns.map((turn, idx) => {
              const preview = (turn.userMsg.content || '').slice(0, 30) + ((turn.userMsg.content?.length || 0) > 30 ? '...' : '')
              return (
                <Tooltip key={turn.userMsg.id}>
                  <TooltipTrigger asChild>
                    <button
                      onClick={() => scrollToTurn(idx)}
                      className={cn(
                        'rounded-full transition-all',
                        idx === visibleTurnIdx
                          ? 'w-2 h-4 bg-primary'
                          : 'w-1.5 h-1.5 bg-muted-foreground/30 hover:bg-muted-foreground/60',
                      )}
                      aria-label={`Turn ${idx + 1}`}
                    />
                  </TooltipTrigger>
                  <TooltipContent side="left" className="max-w-[200px] text-xs">
                    {preview || `Turn ${idx + 1}`}
                  </TooltipContent>
                </Tooltip>
              )
            })}
          </div>
        </TooltipProvider>
      )}

      {showNewContent && (
        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 z-10">
          <Button
            size="sm"
            variant="secondary"
            className="shadow-lg rounded-full gap-1.5 px-4"
            onClick={scrollToBottom}
          >
            <ArrowDown className="h-3.5 w-3.5" />
            {t('chat.newContent')}
          </Button>
        </div>
      )}

      {!readonly && (
        <div className={cn('border-t shrink-0', compact ? 'p-2' : 'p-4')}>
          <div className={cn('flex gap-2', !compact && 'max-w-3xl mx-auto')}>
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder={t('chat.inputPlaceholder')}
              disabled={streaming}
              aria-label={t('chat.inputPlaceholder')}
            />
            {streaming ? (
              <Button
                variant="destructive"
                size={compact ? 'sm' : 'default'}
                onClick={handleStopGeneration}
                aria-label={t('chat.stopGeneration')}
                className="gap-1.5 shrink-0"
              >
                <Square className="h-3.5 w-3.5 fill-current" />
                {!compact && t('chat.stopGeneration')}
              </Button>
            ) : (
              <Button size={compact ? 'sm' : 'default'} onClick={handleSend} disabled={!input.trim()} aria-label={t('chat.send')} className="shrink-0">
                {t('chat.send')}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
