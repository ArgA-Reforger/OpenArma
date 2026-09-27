'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore, useHydrated } from '@/stores/auth'
import { useProjectNavStore } from '@/stores/project-nav'
import { useStreamStore } from '@/stores/stream-store'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ThemeToggle } from '@/components/theme-toggle'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { LogoWithText } from '@/components/logo'
import { downloadConversationHtml } from '@/lib/export-conversation'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import {
  Menu, ChevronLeft, Plus, ChevronDown, ChevronUp,
  MoreHorizontal, Pencil, Pin, PinOff, Share2, Trash2, Copy, Download,
  ShieldCheck, User, Map as MapIcon, Bot, Workflow,
  LayoutGrid, Swords,
} from 'lucide-react'

interface Conversation {
  id: number | string
  title: string | null
  is_pinned: boolean
  share_code?: string | null
  source?: string | null
  side?: string | null
  conversation_group_id?: number | string | null
  status?: string | null
  agent_id?: number | string | null
  topology_id?: number | string | null
  created_time: string
}

interface AgentItem {
  id: number
  name: string
  is_default?: boolean
}

interface TopologyItem {
  id: number
  name: string
}

import type { PageData } from '@/types/resources'

function extractProjectId(pathname: string): string | null {
  const match = pathname.match(/^\/projects\/([^/]+)/)
  return match ? match[1] : null
}

function SidebarLocaleSwitcher() {
  const { locale, setLocale } = useI18n()
  const next = locale === 'es-ES' ? 'en-US' : 'es-ES'
  const label = locale === 'es-ES' ? 'EN' : 'ES'
  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-8 w-8 text-xs font-medium"
      onClick={() => setLocale(next as 'es-ES' | 'en-US')}
      title={next === 'es-ES' ? 'Cambiar a español' : 'Switch to English'}
    >
      {label}
    </Button>
  )
}

function FooterNav({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuthStore()
  const { t } = useI18n()
  const router = useRouter()
  const pathname = usePathname()

  return (
    <>
      <Separator className="my-2" />
      <Link
        href="/resources"
        onClick={onNavigate}
        className={cn(
          'flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent text-muted-foreground',
          pathname === '/resources' && 'bg-accent font-medium text-foreground',
        )}
        aria-current={pathname === '/resources' ? 'page' : undefined}
      >
        <LayoutGrid className="h-4 w-4 shrink-0" />
        {t('nav.resources')}
      </Link>
      <Link
        href="/maps"
        onClick={onNavigate}
        className={cn(
          'flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent text-muted-foreground',
          pathname === '/maps' && 'bg-accent font-medium text-foreground',
        )}
        aria-current={pathname === '/maps' ? 'page' : undefined}
      >
        <MapIcon className="h-4 w-4 shrink-0" />
        {t('nav.maps')}
      </Link>
      <Link
        href="/profile"
        onClick={onNavigate}
        className={cn(
          'flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent text-muted-foreground',
          pathname === '/profile' && 'bg-accent font-medium text-foreground',
        )}
        aria-current={pathname === '/profile' ? 'page' : undefined}
      >
        <User className="h-4 w-4 shrink-0" />
        {t('nav.profile')}
      </Link>
      {(user?.is_superuser || user?.is_staff) && (
        <Link
          href="/admin/dashboard"
          onClick={onNavigate}
          className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent text-muted-foreground"
        >
          <ShieldCheck className="h-4 w-4 shrink-0" />
          {t('nav.backendAdmin')}
        </Link>
      )}
      <div className="flex items-center justify-between mt-1">
        <span className="text-sm text-muted-foreground truncate" title={user?.nickname || user?.username}>
          {user?.nickname || user?.username}
        </span>
        <div className="flex items-center gap-0.5">
          <SidebarLocaleSwitcher />
          <ThemeToggle />
          <Button
            variant="ghost"
            size="sm"
            aria-label={t('auth.logout')}
            onClick={() => {
              logout()
              router.push('/login')
              onNavigate?.()
            }}
          >
            {t('auth.logout')}
          </Button>
        </div>
      </div>
    </>
  )
}

function ProjectListSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const api = useApi()
  const router = useRouter()
  const pathname = usePathname()
  const { t } = useI18n()
  const { setActiveConvId } = useProjectNavStore()
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.get<PageData<{ id: number; name: string; status: string }>>('/projects'),
  })

  const createMutation = useMutation({
    mutationFn: () => api.post<{ id: number | string }>('/projects', { name: t('project.newProject') }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      toast.success(t('project.created'))
      if (data?.id) router.push(`/projects/${data.id}/chat`)
    },
    onError: (err: Error) => toast.error(err.message),
  })

  return (
    <div className="flex flex-col h-full min-h-0">
      <Link href="/projects" className="mb-2 block shrink-0" onClick={onNavigate}>
        <LogoWithText iconSize={22} textClassName="text-lg" />
      </Link>
      <Separator className="my-2 shrink-0" />

      <div className="flex items-center justify-between px-1 mb-1 shrink-0">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {t('nav.projects')}
        </span>
        <button
          onClick={() => !createMutation.isPending && createMutation.mutate()}
          className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground disabled:opacity-50"
          aria-label={t('project.createProject')}
          disabled={createMutation.isPending}
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>

      <ScrollArea className="flex-1 min-h-0 -mx-2 px-2">
        <div className="space-y-0.5">
          {isLoading ? (
            <div className="text-center py-4 text-xs text-muted-foreground">{t('common.loading')}</div>
          ) : !data?.items?.length ? (
            <div className="text-center py-4 text-xs text-muted-foreground">{t('project.emptyHint')}</div>
          ) : (
            data.items.map((project) => {
              const isActive = pathname.startsWith(`/projects/${project.id}`)
              return (
                <button
                  key={project.id}
                  onClick={() => {
                    setActiveConvId(null)
                    router.push(`/projects/${project.id}/chat`)
                    onNavigate?.()
                  }}
                  className={cn(
                    'w-full text-left rounded-md px-3 py-2 text-sm truncate hover:bg-accent',
                    isActive && 'bg-accent font-medium',
                  )}
                >
                  {project.name}
                </button>
              )
            })
          )}
        </div>
      </ScrollArea>

      <div className="shrink-0"><FooterNav onNavigate={onNavigate} /></div>

    </div>
  )
}

interface ConversationGroup {
  id: string
  convs: Conversation[]
  isMulti: boolean
}

function groupConversations(items: Conversation[]): ConversationGroup[] {
  const groupMap = new Map<string, Conversation[]>()
  const soloConvs: Conversation[] = []

  for (const c of items) {
    const gid = c.conversation_group_id
    if (gid) {
      const key = String(gid)
      const arr = groupMap.get(key)
      if (arr) arr.push(c)
      else groupMap.set(key, [c])
    } else {
      soloConvs.push(c)
    }
  }

  const groups: ConversationGroup[] = []

  for (const [key, convs] of groupMap) {
    groups.push({
      id: `group-${key}`,
      convs,
      isMulti: convs.length > 1,
    })
  }

  for (const c of soloConvs) {
    groups.push({ id: String(c.id), convs: [c], isMulti: false })
  }

  return groups
}

const FACTION_COLORS: Record<string, string> = {
  US: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  USSR: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  FIA: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
}

function ConversationGroupItem({
  group, isActive, isStreaming, isRunning, onSelect, onRename, onPin,
  onShare, onUnshare, onCopyShareLink, onExport, onDelete, t,
}: {
  group: ConversationGroup
  isActive: boolean
  isStreaming: boolean
  isRunning?: boolean
  onSelect: () => void
  onRename: () => void
  onPin: () => void
  onShare: () => void
  onUnshare: () => void
  onCopyShareLink: () => void
  onExport: () => void
  onDelete: () => void
  t: (key: string) => string
}) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [hovered, setHovered] = useState(false)
  const showBtn = menuOpen || isActive || hovered
  const primary = group.convs[0]

  return (
    <div
      className={cn(
        'grid rounded-md text-sm',
        isActive ? 'bg-accent' : 'hover:bg-accent/50',
      )}
      style={{ gridTemplateColumns: '1fr 28px' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        onClick={onSelect}
        className="min-w-0 text-left px-3 py-2"
        title={group.isMulti
          ? group.convs.map((c) => c.side || c.title).join(' vs ')
          : primary.title || t('chat.untitled')
        }
      >
        {group.isMulti ? (
          <>
            <div className="flex items-center gap-1.5">
              <Swords className="h-3.5 w-3.5 shrink-0 text-amber-500" />
              {isRunning && <span className="h-2 w-2 shrink-0 rounded-full bg-green-500 animate-pulse" title="Running" />}
              {isStreaming && <span className="h-2 w-2 shrink-0 rounded-full bg-primary animate-pulse" />}
              <span className="truncate font-medium">{primary.title || 'Arma'}</span>
            </div>
            <div className="flex items-center gap-1 mt-1">
              {group.convs.map((c) => (
                <span
                  key={String(c.id)}
                  className={cn(
                    'text-[10px] px-1.5 py-0.5 rounded font-medium',
                    FACTION_COLORS[c.side || ''] || 'bg-muted text-muted-foreground',
                  )}
                >
                  {c.side || '?'}
                </span>
              ))}
            </div>
          </>
        ) : (
          <div className="flex items-center gap-1.5 truncate">
            {primary.is_pinned && <Pin className="h-3 w-3 shrink-0 text-muted-foreground" />}
            {isRunning && <span className="h-2 w-2 shrink-0 rounded-full bg-green-500 animate-pulse" title="Running" />}
            {isStreaming && <span className="h-2 w-2 shrink-0 rounded-full bg-primary animate-pulse" />}
            {primary.side && (
              <span className="shrink-0 text-[10px] px-1 py-0.5 rounded bg-muted font-medium">{primary.side}</span>
            )}
            <span className="truncate">{primary.title || t('chat.untitled')}</span>
          </div>
        )}
      </button>

      <div className="flex items-center justify-center">
        {showBtn && (
          <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen} modal={false}>
            <DropdownMenuTrigger asChild>
              <button
                className="p-1 rounded text-muted-foreground hover:bg-accent hover:text-foreground"
                aria-label="More"
                onClick={(e) => e.stopPropagation()}
              >
                <MoreHorizontal className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" side="bottom" className="w-36">
              <DropdownMenuItem onClick={onRename}>
                <Pencil className="h-4 w-4 mr-2" />{t('chat.rename')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onPin}>
                {primary.is_pinned
                  ? <><PinOff className="h-4 w-4 mr-2" />{t('chat.unpin')}</>
                  : <><Pin className="h-4 w-4 mr-2" />{t('chat.pin')}</>
                }
              </DropdownMenuItem>
              {primary.share_code ? (
                <>
                  <DropdownMenuItem onClick={onCopyShareLink}>
                    <Copy className="h-4 w-4 mr-2" />{t('chat.copyShareLink')}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={onUnshare}>
                    <Share2 className="h-4 w-4 mr-2" />{t('chat.unshare')}
                  </DropdownMenuItem>
                </>
              ) : (
                <DropdownMenuItem onClick={onShare}>
                  <Share2 className="h-4 w-4 mr-2" />{t('chat.share')}
                </DropdownMenuItem>
              )}
              <DropdownMenuItem onClick={onExport}>
                <Download className="h-4 w-4 mr-2" />{t('chat.export')}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={onDelete}
              >
                <Trash2 className="h-4 w-4 mr-2" />{t('common.delete')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </div>
  )
}

function ProjectInternalSidebar({ projectId, onNavigate }: { projectId: string; onNavigate?: () => void }) {
  const api = useApi()
  const router = useRouter()
  const pathname = usePathname()
  const queryClient = useQueryClient()
  const { t } = useI18n()
  const { activeConvId, setActiveConvId } = useProjectNavStore()
  const streamingSet = useStreamStore(
    (s) => {
      const ids: string[] = []
      for (const [k, v] of Object.entries(s.streams)) {
        if (v.streaming) ids.push(k)
      }
      return ids.join(',')
    },
  )

  const [deleteTarget, setDeleteTarget] = useState<ConversationGroup | null>(null)
  const [renameTarget, setRenameTarget] = useState<Conversation | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [createAgentId, setCreateAgentId] = useState<string>('')
  const [createTopologyId, setCreateTopologyId] = useState<string>('')
  const [showAdvanced, setShowAdvanced] = useState(false)

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.get<{ id: number; name: string }>(`/projects/${projectId}`),
  })

  const { data: conversations, isLoading: convsLoading } = useQuery({
    queryKey: ['conversations', projectId],
    queryFn: () => api.get<PageData<Conversation>>(`/projects/${projectId}/conversations?status=active`),
  })

  const { data: agentsList } = useQuery({
    queryKey: ['agents-for-conv'],
    queryFn: () => api.get<PageData<AgentItem>>('/agents'),
    staleTime: 30_000,
  })

  const { data: topologiesList } = useQuery({
    queryKey: ['topologies-for-conv'],
    queryFn: () => api.get<PageData<TopologyItem>>('/topologies'),
    staleTime: 30_000,
  })

  interface ArmaConfigBrief { id: number; conversation_group_id: number | null; running: boolean }
  const { data: armaConfigs } = useQuery({
    queryKey: ['arma-configs', projectId],
    queryFn: () => api.get<ArmaConfigBrief[]>(`/open/admin/${projectId}/arma-configs`),
    staleTime: 10_000,
  })
  const runningGroupIds = new Set(
    (armaConfigs ?? []).filter((c) => c.running && c.conversation_group_id).map((c) => String(c.conversation_group_id)),
  )

  const createConvMutation = useMutation({
    mutationFn: (params: { agent_id?: string | number | null; topology_id?: string | number | null }) =>
      api.post<Conversation>(`/projects/${projectId}/conversations`, {
        title: t('chat.newConversation'),
        agent_id: params.agent_id || null,
        topology_id: params.topology_id || null,
      }),
    onSuccess: (conv) => {
      queryClient.invalidateQueries({ queryKey: ['conversations', projectId] })
      setActiveConvId(conv.id)
      if (!pathname.includes('/chat')) {
        router.push(`/projects/${projectId}/chat`)
      }
      setCreateDialogOpen(false)
      setCreateAgentId('')
      setCreateTopologyId('')
      setShowAdvanced(false)
      onNavigate?.()
    },
  })

  function handleCreateConversation() {
    const agentId = (createAgentId && createAgentId !== '__none__') ? createAgentId : null
    const topoId = (createTopologyId && createTopologyId !== '__none__') ? createTopologyId : null
    createConvMutation.mutate({
      agent_id: topoId ? null : agentId,
      topology_id: topoId,
    })
  }

  const deleteConvMutation = useMutation({
    mutationFn: async (group: ConversationGroup) => {
      for (const c of group.convs) {
        await api.delete(`/projects/${projectId}/conversations/${c.id}`)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations', projectId] })
      queryClient.invalidateQueries({ queryKey: ['arma-configs', projectId] })
      if (deleteTarget && deleteTarget.convs.some((c) => String(c.id) === String(activeConvId))) {
        setActiveConvId(null)
      }
      setDeleteTarget(null)
      toast.success(t('chat.conversationDeleted'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const renameConvMutation = useMutation({
    mutationFn: ({ id, title }: { id: number | string; title: string }) =>
      api.put(`/projects/${projectId}/conversations/${id}`, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations', projectId] })
      setRenameTarget(null)
      toast.success(t('chat.renamed'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const pinConvMutation = useMutation({
    mutationFn: ({ id, is_pinned }: { id: number | string; is_pinned: boolean }) =>
      api.put(`/projects/${projectId}/conversations/${id}`, { is_pinned }),
    onSuccess: (_, { is_pinned }) => {
      queryClient.invalidateQueries({ queryKey: ['conversations', projectId] })
      toast.success(is_pinned ? t('chat.pinned') : t('chat.unpinned'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const shareConvMutation = useMutation({
    mutationFn: (convId: number | string) =>
      api.post<{ share_code: string }>(`/projects/${projectId}/conversations/${convId}/share`),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['conversations', projectId] })
      const shareUrl = `${window.location.origin}/shared/${data.share_code}`
      navigator.clipboard.writeText(shareUrl)
      toast.success(t('chat.shareCopied'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const unshareConvMutation = useMutation({
    mutationFn: (convId: number | string) =>
      api.delete(`/projects/${projectId}/conversations/${convId}/share`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations', projectId] })
      toast.success(t('chat.unshared'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  async function handleExportConversation(convId: number | string, convTitle: string) {
    try {
      interface ExportMsg {
        role: string
        content: string | null
        created_time: string
        metadata?: { agent_id?: number; agent_name?: string; role?: string; is_final?: boolean } | null
      }
      const msgs = await api.get<{ items: ExportMsg[] }>(
        `/projects/${projectId}/conversations/${convId}/messages`
      )
      const items = msgs?.items || []
      if (!items.length) {
        toast.error(t('common.noData'))
        return
      }
      downloadConversationHtml(convTitle, items)
      toast.success(t('chat.exported'))
    } catch {
      toast.error(t('chat.exportFailed'))
    }
  }

  const isOnChat = pathname.includes('/chat')

  const autoCreatingRef = useRef(false)

  useEffect(() => {
    if (activeConvId || convsLoading || !conversations) return
    const items = conversations.items
    if (items && items.length > 0) {
      setActiveConvId(items[0].id)
    } else if (!autoCreatingRef.current) {
      autoCreatingRef.current = true
      createConvMutation.mutate({})
    }
  }, [activeConvId, convsLoading, conversations, setActiveConvId, createConvMutation])

  return (
    <div className="flex flex-col h-full min-h-0">
      <Link href="/projects" className="mb-2 block shrink-0" onClick={onNavigate}>
        <LogoWithText iconSize={22} textClassName="text-lg" />
      </Link>
      <Separator className="my-2 shrink-0" />

      <div className="flex items-center justify-between mb-2 px-1 shrink-0">
        <button
          onClick={() => {
            setActiveConvId(null)
            router.push('/projects')
            onNavigate?.()
          }}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground min-w-0"
        >
          <ChevronLeft className="h-4 w-4 shrink-0" />
          <span className="truncate font-medium">{project?.name || t('common.loading')}</span>
        </button>
      </div>

      <Separator className="mb-2 shrink-0" />

      <div className="flex items-center justify-between px-1 mb-1 shrink-0">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {t('project.chat')}
        </span>
        <button
          onClick={() => setCreateDialogOpen(true)}
          className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground"
          aria-label={t('chat.createConversation')}
          disabled={createConvMutation.isPending}
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>

      <ScrollArea className="flex-1 min-h-0 -mx-2 px-2">
        <div className="space-y-0.5">
          {convsLoading ? (
            <div className="text-center py-4 text-xs text-muted-foreground">{t('common.loading')}</div>
          ) : !conversations?.items?.length ? (
            <div className="text-center py-4 text-xs text-muted-foreground">
              {t('chat.selectHint')}
            </div>
          ) : (() => {
            const groups = groupConversations(conversations.items)
            const primary = (g: ConversationGroup) => g.convs[0]

            return groups.map((group) => {
              const p = primary(group)
              const gid = p.conversation_group_id
              return (
                <ConversationGroupItem
                  key={group.id}
                  group={group}
                  isActive={isOnChat && group.convs.some((c) => String(c.id) === String(activeConvId))}
                  isStreaming={group.convs.some((c) => streamingSet.includes(String(c.id)))}
                  isRunning={!!gid && runningGroupIds.has(String(gid))}
                  onSelect={() => {
                    setActiveConvId(p.id)
                    if (!isOnChat) router.push(`/projects/${projectId}/chat`)
                    onNavigate?.()
                  }}
                  onRename={() => { setRenameTarget(p); setRenameValue(p.title || '') }}
                  onPin={() => pinConvMutation.mutate({ id: p.id, is_pinned: !p.is_pinned })}
                  onShare={() => shareConvMutation.mutate(p.id)}
                  onUnshare={() => unshareConvMutation.mutate(p.id)}
                  onCopyShareLink={() => {
                    if (p.share_code) {
                      navigator.clipboard.writeText(`${window.location.origin}/shared/${p.share_code}`)
                      toast.success(t('chat.shareCopied'))
                    }
                  }}
                  onExport={() => handleExportConversation(p.id, p.title || t('chat.untitled'))}
                  onDelete={() => setDeleteTarget(group)}
                  t={t}
                />
              )
            })
          })()}
        </div>
      </ScrollArea>

      <div className="shrink-0"><FooterNav onNavigate={onNavigate} /></div>

      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('chat.deleteConversation')}</AlertDialogTitle>
            <AlertDialogDescription>{t('chat.confirmDeleteConversation')}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={() => { if (deleteTarget) deleteConvMutation.mutate(deleteTarget) }}>
              {t('common.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={!!renameTarget} onOpenChange={(open) => !open && setRenameTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('chat.renameConversation')}</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              if (renameTarget && renameValue.trim()) {
                renameConvMutation.mutate({ id: renameTarget.id, title: renameValue.trim() })
              }
            }}
            className="space-y-4"
          >
            <Input value={renameValue} onChange={(e) => setRenameValue(e.target.value)} required autoFocus />
            <DialogFooter>
              <Button type="submit" disabled={renameConvMutation.isPending}>
                {renameConvMutation.isPending ? t('common.saving') : t('common.save')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={createDialogOpen} onOpenChange={(open) => {
        if (!open) {
          setCreateDialogOpen(false)
          setCreateAgentId('')
          setCreateTopologyId('')
          setShowAdvanced(false)
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t('chat.createConversation')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label className="flex items-center gap-1.5">
                <Bot className="h-3.5 w-3.5" />
                {t('chat.selectAgent')}
              </Label>
              <Select value={createAgentId} onValueChange={(v) => { setCreateAgentId(v); if (v) setCreateTopologyId('') }}>
                <SelectTrigger>
                  <SelectValue placeholder={t('chat.noAgent')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">{t('chat.noAgent')}</SelectItem>
                  {agentsList?.items?.map((a) => (
                    <SelectItem key={a.id} value={String(a.id)}>
                      {a.name}{a.is_default ? ` ★` : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              {showAdvanced ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {t('chat.advancedOptions')}
            </button>

            {showAdvanced && (
              <div className="space-y-2">
                <Label className="flex items-center gap-1.5">
                  <Workflow className="h-3.5 w-3.5" />
                  {t('chat.useTopology')}
                </Label>
                <Select value={createTopologyId} onValueChange={(v) => { setCreateTopologyId(v); if (v && v !== '__none__') setCreateAgentId('') }}>
                  <SelectTrigger>
                    <SelectValue placeholder={t('chat.noneSelected')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">{t('chat.noneSelected')}</SelectItem>
                    {topologiesList?.items?.map((tp) => (
                      <SelectItem key={tp.id} value={String(tp.id)}>
                        {tp.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground italic">
                  {t('chat.useTopology')}
                </p>
              </div>
            )}
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={handleCreateConversation} disabled={createConvMutation.isPending}>
              {createConvMutation.isPending ? t('common.loading') : t('common.create')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()
  const projectId = extractProjectId(pathname)

  if (projectId) {
    return <ProjectInternalSidebar projectId={projectId} onNavigate={onNavigate} />
  }
  return <ProjectListSidebar onNavigate={onNavigate} />
}

export default function UserLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { token } = useAuthStore()
  const hydrated = useHydrated()
  const [sheetOpen, setSheetOpen] = useState(false)

  useEffect(() => {
    if (hydrated && !token) router.push('/login')
  }, [hydrated, token, router])

  if (!hydrated || !token) return null

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="hidden md:flex w-60 border-r bg-muted/40 p-4 flex-col shrink-0 overflow-hidden">
        <SidebarContent />
      </aside>

      <div className="flex-1 flex flex-col">
        <header className="md:hidden flex items-center gap-2 border-b px-4 py-2">
          <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Menu">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-60 p-4 flex flex-col">
              <SidebarContent onNavigate={() => setSheetOpen(false)} />
            </SheetContent>
          </Sheet>
          <LogoWithText iconSize={20} textClassName="text-base" />
        </header>
        <main className="flex-1 flex flex-col overflow-hidden">{children}</main>
      </div>
      
    </div>
  )
}
