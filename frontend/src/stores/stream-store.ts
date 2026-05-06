import { create } from 'zustand'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1'

export interface AgentOutput {
  agentId: number
  agentName: string
  content: string
}

export interface MultiAgentResponse {
  agents: AgentOutput[]
  finalContent: string
  finalRole: string
}

export interface NodeExecutionState {
  nodeId: string
  nodeType: string
  agentId?: number
  agentName?: string
  status: 'running' | 'completed' | 'error'
}

export interface ToolCallEvent {
  toolName: string
  toolType: string
  displayName?: string
  arguments: Record<string, unknown>
  status: 'calling' | 'success' | 'error'
  result?: string
}

export interface StreamState {
  streaming: boolean
  streamContent: string
  multiAgentStream: MultiAgentResponse | null
  activeAgentName: string | null
  abortController: AbortController | null
  completedMessages: StreamCompletedMessage[] | null
  dagNodeStates: NodeExecutionState[]
  toolCalls: ToolCallEvent[]
}

export interface StreamCompletedMessage {
  id: number
  role: string
  content: string
  created_time: string
  metadata?: {
    agent_id?: number
    agent_name?: string
    role?: string
    is_final?: boolean
  } | null
}

function parseSSEData(raw: string): { isMultiAgent: boolean; plainToken?: string; event?: Record<string, unknown> } {
  const trimmed = raw.trim()
  if (!trimmed) return { isMultiAgent: false }
  if (trimmed.startsWith('{')) {
    try {
      const parsed = JSON.parse(trimmed)
      if (parsed.type) return { isMultiAgent: true, event: parsed }
    } catch { /* not JSON */ }
  }
  return { isMultiAgent: false, plainToken: raw }
}

type ConvKey = number | string

interface StreamStore {
  streams: Record<ConvKey, StreamState>
  getStream: (convId: ConvKey) => StreamState | undefined
  isStreaming: (convId: ConvKey) => boolean
  startStream: (params: {
    pid: string
    convId: ConvKey
    content: string
    resend: boolean
    needsTitle?: boolean
    onTitleGenerated?: () => void
  }) => void
  abortStream: (convId: ConvKey) => void
  clearStream: (convId: ConvKey) => void
}

const emptyStream: StreamState = {
  streaming: false,
  streamContent: '',
  multiAgentStream: null,
  activeAgentName: null,
  abortController: null,
  completedMessages: null,
  dagNodeStates: [],
  toolCalls: [],
}

export const useStreamStore = create<StreamStore>()((set, get) => {
  function updateStream(convId: ConvKey, patch: Partial<StreamState>) {
    set((state) => ({
      streams: {
        ...state.streams,
        [convId]: { ...(state.streams[convId] ?? emptyStream), ...patch },
      },
    }))
  }

  async function runStream(params: {
    pid: string
    convId: ConvKey
    content: string
    resend: boolean
    needsTitle?: boolean
    onTitleGenerated?: () => void
  }) {
    const { pid, convId, content, resend, needsTitle, onTitleGenerated } = params
    const token = useAuthStore.getState().token

    const controller = new AbortController()
    updateStream(convId, {
      streaming: true,
      streamContent: '',
      multiAgentStream: null,
      activeAgentName: null,
      abortController: controller,
      completedMessages: null,
      dagNodeStates: [],
      toolCalls: [],
    })

    const endpoint = resend
      ? `${API_BASE}/projects/${pid}/conversations/${convId}/resend`
      : `${API_BASE}/projects/${pid}/conversations/${convId}/messages`

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content }),
        signal: controller.signal,
      })

      if (response.status === 401) {
        const { useAuthStore } = await import('@/stores/auth')
        useAuthStore.getState().logout()
        if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
          window.location.href = '/login'
        }
        throw new Error('Unauthorized')
      }

      if (!response.ok || !response.body) {
        const errText = await response.text().catch(() => 'Request failed')
        toast.error(errText || 'Request failed')
        throw new Error(errText || 'Request failed')
      }

      if (needsTitle) {
        api.post(`/projects/${pid}/conversations/${convId}/generate-title`, undefined, {
          token: token ?? undefined,
        }).then(() => onTitleGenerated?.()).catch(() => { /* best-effort */ })
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let isMultiAgentMode = false
      let plainFullContent = ''
      const agentBuffers = new Map<number, { name: string; content: string }>()
      let finalBuffer = ''
      let finalRole = 'coordinator'
      let inFinalPhase = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        const lines = text.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6)
          if (data === '[DONE]') continue

          const { isMultiAgent, plainToken, event } = parseSSEData(data)

          if (!isMultiAgent && plainToken !== undefined) {
            plainFullContent += plainToken
            updateStream(convId, { streamContent: plainFullContent })
            continue
          }

          if (isMultiAgent && event) {
            if (event.error) {
              console.error('[stream] Backend error:', event.error)
              plainFullContent += `\n\n⚠️ ${event.error}`
              updateStream(convId, { streamContent: plainFullContent })
              continue
            }

            isMultiAgentMode = true
            const eventType = event.type as string

            if (eventType === 'error') {
              console.error('[stream] Graph error:', event.content)
              plainFullContent += `\n\n⚠️ ${event.content || 'Unknown error'}`
              updateStream(convId, { streamContent: plainFullContent })
              continue
            }

            switch (eventType) {
              case 'agent_start': {
                const aid = event.agent_id as number
                const aname = event.agent_name as string
                inFinalPhase = false
                if (!agentBuffers.has(aid)) {
                  agentBuffers.set(aid, { name: aname, content: '' })
                }
                updateStream(convId, { activeAgentName: aname })
                break
              }
              case 'agent_end':
                updateStream(convId, { activeAgentName: null })
                break
              case 'coordinator_start':
                inFinalPhase = true
                finalRole = 'coordinator'
                updateStream(convId, { activeAgentName: 'Coordinator' })
                break
              case 'coordinator_end':
                inFinalPhase = false
                updateStream(convId, { activeAgentName: null })
                break
              case 'aggregator_start':
                inFinalPhase = true
                finalRole = 'aggregator'
                updateStream(convId, { activeAgentName: 'Aggregator' })
                break
              case 'aggregator_end':
                inFinalPhase = false
                updateStream(convId, { activeAgentName: null })
                break
              case 'node_start': {
                const nodeId = event.node_id as string
                const nodeType = event.node_type as string
                const nodeAgentId = event.agent_id as number | undefined
                const nodeAgentName = event.agent_name as string | undefined

                if (nodeType === 'agent' && nodeAgentId != null) {
                  inFinalPhase = false
                  if (!agentBuffers.has(nodeAgentId)) {
                    agentBuffers.set(nodeAgentId, { name: nodeAgentName || `Agent ${nodeAgentId}`, content: '' })
                  }
                  updateStream(convId, { activeAgentName: nodeAgentName || null })
                }

                const currentStates = get().streams[convId]?.dagNodeStates || []
                const newState: NodeExecutionState = {
                  nodeId, nodeType, agentId: nodeAgentId, agentName: nodeAgentName, status: 'running',
                }
                updateStream(convId, {
                  dagNodeStates: [...currentStates.filter((s) => s.nodeId !== nodeId), newState],
                })
                break
              }
              case 'node_end': {
                const endNodeId = event.node_id as string
                const currentNodeStates = get().streams[convId]?.dagNodeStates || []
                updateStream(convId, {
                  dagNodeStates: currentNodeStates.map((s) =>
                    s.nodeId === endNodeId ? { ...s, status: 'completed' as const } : s,
                  ),
                  activeAgentName: null,
                })
                break
              }
              case 'sub_agent_start': {
                const subName = event.agent_name as string
                updateStream(convId, { activeAgentName: `⚡ ${subName}` })
                break
              }
              case 'sub_agent_end':
                updateStream(convId, { activeAgentName: null })
                break
              case 'coordinator_followup': {
                const round = event.round as number
                updateStream(convId, { activeAgentName: `Coordinator (Round ${round})` })
                break
              }
              case 'tool_call': {
                const tcName = event.tool_name as string
                const tcType = event.tool_type as string
                const tcDisplayName = (event.display_name as string) || ''
                const tcArgs = (event.arguments as Record<string, unknown>) || {}
                const prev = get().streams[convId]?.toolCalls || []
                updateStream(convId, {
                  toolCalls: [...prev, { toolName: tcName, toolType: tcType, displayName: tcDisplayName, arguments: tcArgs, status: 'calling' }],
                })
                break
              }
              case 'tool_result': {
                const trName = event.tool_name as string
                const trResult = (event.result as string) || ''
                const trError = event.error as boolean | undefined
                const prevCalls = get().streams[convId]?.toolCalls || []
                const idx = [...prevCalls].reverse().findIndex((tc) => tc.toolName === trName && tc.status === 'calling')
                if (idx >= 0) {
                  const realIdx = prevCalls.length - 1 - idx
                  const updated = [...prevCalls]
                  updated[realIdx] = { ...updated[realIdx], status: trError ? 'error' : 'success', result: trResult }
                  updateStream(convId, { toolCalls: updated })
                }
                break
              }
              case 'token': {
                const tokenContent = (event.content as string) || ''
                const tokenAgentId = event.agent_id as number | undefined

                if (inFinalPhase) {
                  finalBuffer += tokenContent
                } else if (tokenAgentId != null && agentBuffers.has(tokenAgentId)) {
                  const buf = agentBuffers.get(tokenAgentId)!
                  buf.content += tokenContent
                }

                updateStream(convId, {
                  multiAgentStream: {
                    agents: Array.from(agentBuffers.entries()).map(([id, buf]) => ({
                      agentId: id,
                      agentName: buf.name,
                      content: buf.content,
                    })),
                    finalContent: finalBuffer,
                    finalRole,
                  },
                })
                break
              }
            }
          }
        }
      }

      const completedMessages: StreamCompletedMessage[] = []
      const now = Date.now()
      if (isMultiAgentMode) {
        agentBuffers.forEach((buf, aid) => {
          if (buf.content) {
            completedMessages.push({
              id: now + aid,
              role: 'assistant',
              content: buf.content,
              created_time: new Date().toISOString(),
              metadata: { agent_id: aid, agent_name: buf.name, role: 'agent' },
            })
          }
        })
        if (finalBuffer) {
          completedMessages.push({
            id: now + 99999,
            role: 'assistant',
            content: finalBuffer,
            created_time: new Date().toISOString(),
            metadata: { role: finalRole, is_final: true },
          })
        }
      } else if (plainFullContent) {
        completedMessages.push({
          id: now + 1,
          role: 'assistant',
          content: plainFullContent,
          created_time: new Date().toISOString(),
        })
      }

      updateStream(convId, {
        streaming: false,
        streamContent: '',
        multiAgentStream: null,
        activeAgentName: null,
        abortController: null,
        completedMessages,
        toolCalls: [],
      })
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        updateStream(convId, {
          streaming: false,
          abortController: null,
        })
        return
      }
      const msg = err instanceof Error ? err.message : 'Stream error'
      toast.error(msg)
      updateStream(convId, {
        streaming: false,
        streamContent: '',
        multiAgentStream: null,
        activeAgentName: null,
        abortController: null,
        completedMessages: null,
      })
    }
  }

  return {
    streams: {},
    getStream: (convId) => get().streams[convId],
    isStreaming: (convId) => get().streams[convId]?.streaming ?? false,
    startStream: (params) => { runStream(params) },
    abortStream: (convId) => {
      const stream = get().streams[convId]
      if (stream?.abortController) {
        stream.abortController.abort()
      }
    },
    clearStream: (convId) => {
      set((state) => {
        const { [convId]: _, ...rest } = state.streams
        return { streams: rest }
      })
    },
  }
})
