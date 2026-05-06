'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { useI18n } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { Search, Bot, BookOpen, Wrench, Cpu, Workflow } from 'lucide-react'
import {
  AgentsShowcase,
  KnowledgeShowcase,
  MCPShowcase,
  LLMShowcase,
  TopologyShowcase,
} from '../resources/_components/showcase'

type Tab = 'agents' | 'knowledge' | 'mcps' | 'llm' | 'topology'

export default function ShowcasePage() {
  const { t } = useI18n()
  const [tab, setTab] = useState<Tab>('agents')
  const [keyword, setKeyword] = useState('')

  const tabs: { key: Tab; label: string; icon: React.ReactNode; disabled?: boolean }[] = [
    { key: 'agents', label: t('agent.title'), icon: <Bot className="h-4 w-4" /> },
    { key: 'knowledge', label: t('knowledge.title'), icon: <BookOpen className="h-4 w-4" />, disabled: true },
    { key: 'mcps', label: t('mcp.title'), icon: <Wrench className="h-4 w-4" />, disabled: true },
    { key: 'llm', label: t('llm.title'), icon: <Cpu className="h-4 w-4" /> },
    { key: 'topology', label: t('topology.title'), icon: <Workflow className="h-4 w-4" /> },
  ]

  return (
    <div className="p-6 overflow-auto flex-1">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{t('showcase.title')}</h1>
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder={t('common.search')}
            className="pl-9"
          />
        </div>
      </div>

      <div className="flex gap-2 mb-6">
        {tabs.map((tabItem) => (
          <button
            key={tabItem.key}
            onClick={() => !tabItem.disabled && setTab(tabItem.key)}
            disabled={tabItem.disabled}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              tabItem.disabled
                ? 'opacity-50 cursor-not-allowed bg-muted text-muted-foreground'
                : tab === tabItem.key
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-accent hover:text-foreground',
            )}
          >
            {tabItem.icon}
            {tabItem.label}
          </button>
        ))}
      </div>

      {tab === 'agents' && <AgentsShowcase keyword={keyword} />}
      {tab === 'knowledge' && <KnowledgeShowcase keyword={keyword} />}
      {tab === 'mcps' && <MCPShowcase keyword={keyword} />}
      {tab === 'llm' && <LLMShowcase keyword={keyword} />}
      {tab === 'topology' && <TopologyShowcase keyword={keyword} />}
    </div>
  )
}
