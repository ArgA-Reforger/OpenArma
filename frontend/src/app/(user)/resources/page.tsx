'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useI18n } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { ChevronDown, ChevronRight, Cpu, Bot, BookOpen, Plug, Wrench, Workflow, Globe, User, Plus, Lock } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { EmbeddedProps } from '@/types/resources'

import { LLMProvidersPage } from './_components/llm-providers'
import { AgentsPage } from './_components/agents'
import { KnowledgePage } from './_components/knowledge'
import { MCPServersPage } from './_components/mcp-servers'
import { BuiltinToolsPage } from './_components/builtin-tools'
import { TopologiesPage } from './_components/topologies'
import { AgentsShowcase, KnowledgeShowcase, MCPShowcase, LLMShowcase, TopologyShowcase } from './_components/showcase'

type ViewMode = 'mine' | 'community'

interface SectionConfig {
  id: string
  icon: React.ComponentType<{ className?: string }>
  key: string
  hasAdd: boolean
  Component: React.ComponentType<EmbeddedProps>
  CommunityComponent?: React.ComponentType<{ keyword: string; visibilityFilter?: string }>
  disabled?: boolean
  disabledKey?: string
}

const SECTIONS: SectionConfig[] = [
  { id: 'llm', icon: Cpu, key: 'nav.llmProviders', hasAdd: true, Component: LLMProvidersPage, CommunityComponent: LLMShowcase },
  { id: 'agents', icon: Bot, key: 'nav.agents', hasAdd: true, Component: AgentsPage, CommunityComponent: AgentsShowcase },
  { id: 'knowledge', icon: BookOpen, key: 'nav.knowledgeBases', hasAdd: true, Component: KnowledgePage, CommunityComponent: KnowledgeShowcase, disabled: true, disabledKey: 'knowledge.comingSoon' },
  { id: 'mcp', icon: Plug, key: 'nav.mcpServers', hasAdd: true, Component: MCPServersPage, CommunityComponent: MCPShowcase, disabled: true, disabledKey: 'mcp.comingSoon' },
  { id: 'topology', icon: Workflow, key: 'nav.topologies', hasAdd: true, Component: TopologiesPage as React.ComponentType<EmbeddedProps>, CommunityComponent: TopologyShowcase },
  { id: 'builtin', icon: Wrench, key: 'nav.builtinTools', hasAdd: false, Component: BuiltinToolsPage as React.ComponentType<EmbeddedProps> },
]

export default function ResourcesPage() {
  const { t } = useI18n()
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [viewModes, setViewModes] = useState<Record<string, ViewMode>>({})
  const [addDialogId, setAddDialogId] = useState<string | null>(null)
  const [activeAnchor, setActiveAnchor] = useState(SECTIONS[0].id)
  const scrollRef = useRef<HTMLDivElement>(null)
  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({})

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function setViewMode(id: string, mode: ViewMode) {
    setViewModes((prev) => ({ ...prev, [id]: mode }))
  }

  function handleAdd(id: string) {
    const section = SECTIONS.find((s) => s.id === id)
    if (section?.disabled) return
    if (!expanded.has(id)) {
      setExpanded((prev) => new Set(prev).add(id))
    }
    setViewModes((prev) => ({ ...prev, [id]: 'mine' }))
    setAddDialogId(id)
  }

  function scrollToSection(id: string) {
    const el = sectionRefs.current[id]
    if (el && scrollRef.current) {
      const top = el.offsetTop - scrollRef.current.offsetTop
      scrollRef.current.scrollTo({ top, behavior: 'smooth' })
    }
    const section = SECTIONS.find((s) => s.id === id)
    if (!section?.disabled && !expanded.has(id)) {
      setExpanded((prev) => new Set(prev).add(id))
    }
  }

  const handleScroll = useCallback(() => {
    const container = scrollRef.current
    if (!container) return
    const scrollTop = container.scrollTop + 80
    let current = SECTIONS[0].id
    for (const { id } of SECTIONS) {
      const el = sectionRefs.current[id]
      if (el && el.offsetTop - container.offsetTop <= scrollTop) {
        current = id
      }
    }
    setActiveAnchor(current)
  }, [])

  useEffect(() => {
    const container = scrollRef.current
    if (!container) return
    container.addEventListener('scroll', handleScroll, { passive: true })
    return () => container.removeEventListener('scroll', handleScroll)
  }, [handleScroll])

  return (
    <div className="flex flex-1 overflow-hidden">
      <div ref={scrollRef} className="flex-1 overflow-auto scrollbar-thin">
        <div className="px-6 pt-6 pb-6 space-y-4 mr-2">
          {SECTIONS.map(({ id, icon: Icon, key, hasAdd, Component, CommunityComponent, disabled, disabledKey }) => {
            const isOpen = !disabled && expanded.has(id)
            const mode = viewModes[id] || 'mine'
            const hasCommunity = !!CommunityComponent
            return (
              <div
                key={id}
                ref={(el) => { sectionRefs.current[id] = el }}
                className={cn("rounded-xl border bg-card shadow-sm", disabled && "opacity-60")}
              >
                <div
                  className={cn(
                    "flex items-center justify-between px-4 py-3 bg-muted/30 rounded-t-xl transition-colors",
                    disabled ? "cursor-default" : "cursor-pointer hover:bg-muted/50",
                  )}
                  onClick={() => !disabled && toggle(id)}
                >
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-2.5">
                      {disabled ? (
                        <Lock className="h-4 w-4 text-muted-foreground" />
                      ) : isOpen ? (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      )}
                      <div className={cn("flex items-center justify-center h-7 w-7 rounded-lg", disabled ? "bg-muted" : "bg-primary/10")}>
                        <Icon className={cn("h-4 w-4", disabled ? "text-muted-foreground" : "text-primary")} />
                      </div>
                      <span className="font-semibold text-sm">{t(key)}</span>
                      {disabled && disabledKey && (
                        <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                          {t(disabledKey)}
                        </Badge>
                      )}
                    </div>

                    {!disabled && hasAdd && mode === 'mine' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleAdd(id) }}
                        className="flex items-center justify-center h-6 w-6 rounded-md border bg-background text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                        title={t('common.create')}
                      >
                        <Plus className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>

                  {!disabled && hasCommunity && isOpen && (
                    <div className="flex items-center rounded-lg border bg-background p-0.5" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => setViewMode(id, 'mine')}
                        className={cn(
                          'flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all',
                          mode === 'mine'
                            ? 'bg-primary text-primary-foreground shadow-sm'
                            : 'text-muted-foreground hover:text-foreground',
                        )}
                      >
                        <User className="h-3 w-3" />
                        {t('nav.myResources')}
                      </button>
                      <button
                        onClick={() => setViewMode(id, 'community')}
                        className={cn(
                          'flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all',
                          mode === 'community'
                            ? 'bg-primary text-primary-foreground shadow-sm'
                            : 'text-muted-foreground hover:text-foreground',
                        )}
                      >
                        <Globe className="h-3 w-3" />
                        {t('nav.communityResources')}
                      </button>
                    </div>
                  )}
                </div>

                {isOpen && (
                  <div className="border-t">
                    {mode === 'mine' || !CommunityComponent ? (
                      <Component
                        embedded
                        addDialogOpen={addDialogId === id}
                        onAddDialogOpenChange={(v) => { if (!v) setAddDialogId(null) }}
                      />
                    ) : (
                      <div className="p-6">
                        <CommunityComponent keyword="" />
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      <nav className="hidden md:flex w-16 lg:w-32 shrink-0 flex-col items-center justify-center gap-1.5 border-l bg-background/80 px-2 py-4">
        {SECTIONS.map(({ id, icon: Icon, key, disabled, disabledKey }) => {
          const isActive = activeAnchor === id
          return (
            <button
              key={id}
              onClick={() => scrollToSection(id)}
              className={cn(
                'flex flex-col lg:flex-row items-center gap-1 lg:gap-2 px-2 py-2 rounded-lg transition-all text-[10px] lg:text-xs w-full',
                disabled
                  ? 'opacity-50 cursor-default text-muted-foreground'
                  : isActive
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent',
              )}
              title={disabled && disabledKey ? t(disabledKey) : t(key)}
            >
              <Icon className={cn('h-4 w-4 shrink-0', !disabled && isActive && 'text-primary')} />
              <span className="hidden lg:inline whitespace-nowrap truncate">{t(key)}</span>
            </button>
          )
        })}
      </nav>
    </div>
  )
}
