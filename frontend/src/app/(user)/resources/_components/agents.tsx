'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from '@/components/ui/tooltip'
import { Checkbox } from '@/components/ui/checkbox'
import { HelpCircle, Copy } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useResourceCRUD } from '@/hooks/use-resource-crud'
import { DeleteConfirmDialog } from '@/components/resource/delete-confirm-dialog'
import type { EmbeddedProps, PageData, LLMProviderBase } from '@/types/resources'

interface BuiltinToolConfig {
  enabled: boolean
}

interface Agent {
  id: number
  name: string
  description: string | null
  system_prompt: string | null
  rules: string[] | null
  model_name: string | null
  temperature: number
  top_p: number | null
  max_tokens: number | null
  presence_penalty: number | null
  frequency_penalty: number | null
  llm_provider_id: number | null
  visibility: string
  builtin_tools: Record<string, BuiltinToolConfig> | null
  enable_sub_agents: boolean
  created_time: string
}

interface BuiltinToolInfo {
  id: number
  name: string
  display_name: string
  description: string
  category: string
}

function groupToolsByCategory(tools: BuiltinToolInfo[]): [string, BuiltinToolInfo[]][] {
  const map = new Map<string, BuiltinToolInfo[]>()
  for (const t of tools) {
    const cat = t.category || 'general'
    if (!map.has(cat)) map.set(cat, [])
    map.get(cat)!.push(t)
  }
  const entries = [...map.entries()]
  entries.sort(([a], [b]) => (a === 'general' ? -1 : b === 'general' ? 1 : a.localeCompare(b)))
  return entries
}

function ParamRow({
  id,
  label,
  help,
  enabled,
  onToggle,
  children,
}: {
  id: string
  label: string
  help: string
  enabled: boolean
  onToggle: (v: boolean) => void
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <Checkbox id={`chk-${id}`} checked={enabled} onCheckedChange={(v) => onToggle(!!v)} />
        <Label htmlFor={`chk-${id}`} className="text-sm cursor-pointer">{label}</Label>
        <TooltipProvider delayDuration={200}>
          <Tooltip>
            <TooltipTrigger asChild>
              <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-xs text-xs">
              {help}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      <div className={enabled ? '' : 'opacity-40 pointer-events-none'}>
        {children}
      </div>
    </div>
  )
}

export function AgentsPage({ embedded, addDialogOpen, onAddDialogOpenChange }: EmbeddedProps = {}) {
  const api = useApi()
  const [internalOpen, setInternalOpen] = useState(false)
  const open = addDialogOpen ?? internalOpen
  const setOpen = onAddDialogOpenChange ?? setInternalOpen
  const [editOpen, setEditOpen] = useState(false)
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null)
  const [providerType, setProviderType] = useState<string>('')
  const [editProviderType, setEditProviderType] = useState<string>('')
  const [deleteTarget, setDeleteTarget] = useState<Agent | null>(null)
  const [createBuiltinTools, setCreateBuiltinTools] = useState<Record<string, boolean>>({})
  const [editBuiltinTools, setEditBuiltinTools] = useState<Record<string, boolean>>({})
  const [createSubAgents, setCreateSubAgents] = useState(false)
  const [editSubAgents, setEditSubAgents] = useState(false)
  const [createRules, setCreateRules] = useState<string[]>([])
  const [editRules, setEditRules] = useState<string[]>([])
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showEditAdvanced, setShowEditAdvanced] = useState(false)
  const [createParamEnabled, setCreateParamEnabled] = useState<Record<string, boolean>>({})
  const [editParamEnabled, setEditParamEnabled] = useState<Record<string, boolean>>({})
  const { t } = useI18n()

  const {
    items, isLoading, isError,
    createMutation, updateMutation, deleteMutation, cloneMutation,
  } = useResourceCRUD<Agent>({
    endpoint: '/agents',
    queryKey: ['agents'],
    toastKeys: { created: 'agent.created', updated: 'agent.updated', deleted: 'agent.deleted', cloned: 'common.cloneSuccess' },
    onCreateSuccess: () => {
      setOpen(false)
      setCreateBuiltinTools({})
      setCreateSubAgents(false)
      setCreateRules([])
    },
    onUpdateSuccess: () => {
      setEditOpen(false)
      setEditingAgent(null)
    },
  })

  const { data: providers } = useQuery({
    queryKey: ['llm-providers'],
    queryFn: () => api.get<PageData<LLMProviderBase>>('/llm-providers'),
  })

  const { data: builtinTools } = useQuery({
    queryKey: ['builtin-tools-active'],
    queryFn: () => api.get<BuiltinToolInfo[]>('/builtin-tools/active'),
  })

  function buildBuiltinToolsPayload(toggles: Record<string, boolean>): Record<string, BuiltinToolConfig> | undefined {
    const result: Record<string, BuiltinToolConfig> = {}
    let hasAny = false
    for (const [name, enabled] of Object.entries(toggles)) {
      if (enabled) {
        result[name] = { enabled: true }
        hasAny = true
      }
    }
    return hasAny ? result : undefined
  }

  function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const topP = fd.get('top_p') as string
    const maxTokens = fd.get('max_tokens') as string
    const presencePenalty = fd.get('presence_penalty') as string
    const frequencyPenalty = fd.get('frequency_penalty') as string
    const filteredCreateRules = createRules.filter(r => r.trim())
    createMutation.mutate({
      name: fd.get('name') as string,
      description: (fd.get('description') as string) || undefined,
      system_prompt: (fd.get('system_prompt') as string) || undefined,
      rules: filteredCreateRules.length > 0 ? filteredCreateRules : undefined,
      llm_provider_id: providerType || undefined,
      model_name: (fd.get('model_name') as string) || undefined,
      temperature: Number(fd.get('temperature')) || 0.7,
      top_p: createParamEnabled.top_p && topP ? Number(topP) : null,
      max_tokens: createParamEnabled.max_tokens && maxTokens ? Number(maxTokens) : null,
      presence_penalty: createParamEnabled.presence_penalty && presencePenalty ? Number(presencePenalty) : null,
      frequency_penalty: createParamEnabled.frequency_penalty && frequencyPenalty ? Number(frequencyPenalty) : null,
      visibility: (fd.get('visibility') as string) || 'private',
      builtin_tools: buildBuiltinToolsPayload(createBuiltinTools),
      enable_sub_agents: createSubAgents,
    })
  }

  function handleEdit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!editingAgent) return
    const fd = new FormData(e.currentTarget)
    const topP = fd.get('top_p') as string
    const maxTokens = fd.get('max_tokens') as string
    const presencePenalty = fd.get('presence_penalty') as string
    const frequencyPenalty = fd.get('frequency_penalty') as string
    const filteredEditRules = editRules.filter(r => r.trim())
    updateMutation.mutate({
      id: editingAgent.id,
      body: {
        name: fd.get('name') as string,
        description: (fd.get('description') as string) || undefined,
        system_prompt: (fd.get('system_prompt') as string) || undefined,
        rules: filteredEditRules.length > 0 ? filteredEditRules : [],
        llm_provider_id: editProviderType || undefined,
        model_name: (fd.get('model_name') as string) || undefined,
        temperature: Number(fd.get('temperature')) || 0.7,
        top_p: editParamEnabled.top_p && topP ? Number(topP) : null,
        max_tokens: editParamEnabled.max_tokens && maxTokens ? Number(maxTokens) : null,
        presence_penalty: editParamEnabled.presence_penalty && presencePenalty ? Number(presencePenalty) : null,
        frequency_penalty: editParamEnabled.frequency_penalty && frequencyPenalty ? Number(frequencyPenalty) : null,
        visibility: (fd.get('visibility') as string) || 'private',
        builtin_tools: buildBuiltinToolsPayload(editBuiltinTools),
        enable_sub_agents: editSubAgents,
      },
    })
  }

  function openEditDialog(agent: Agent) {
    setEditingAgent(agent)
    setEditProviderType(agent.llm_provider_id ? String(agent.llm_provider_id) : '')
    const toggles: Record<string, boolean> = {}
    if (agent.builtin_tools) {
      for (const [name, cfg] of Object.entries(agent.builtin_tools)) {
        toggles[name] = cfg?.enabled ?? false
      }
    }
    setEditBuiltinTools(toggles)
    setEditSubAgents(agent.enable_sub_agents ?? false)
    setEditRules(Array.isArray(agent.rules) ? [...agent.rules] : [])
    setEditParamEnabled({
      top_p: agent.top_p != null,
      max_tokens: agent.max_tokens != null,
      presence_penalty: agent.presence_penalty != null,
      frequency_penalty: agent.frequency_penalty != null,
    })
    setShowEditAdvanced(agent.top_p != null || agent.max_tokens != null || agent.presence_penalty != null || agent.frequency_penalty != null)
    setEditOpen(true)
  }

  function renderBuiltinToolsSection(toggles: Record<string, boolean>, setToggles: (fn: (prev: Record<string, boolean>) => Record<string, boolean>) => void) {
    if (!builtinTools || builtinTools.length === 0) return null
    return (
      <div className="space-y-3">
        <Label>{t('agent.builtinTools')}</Label>
        <div className="space-y-2 rounded-md border p-3">
          {groupToolsByCategory(builtinTools).map(([cat, tools]) => (
            <div key={cat}>
              {cat !== 'general' && (
                <p className="text-xs font-semibold text-amber-600 uppercase tracking-wider mb-1 mt-2">{cat}</p>
              )}
              {tools.map((tool) => (
                <div key={tool.name} className="flex items-center justify-between py-0.5">
                  <div>
                    <span className="text-sm font-medium">{(() => { const k = `builtinTool.tool_${tool.name}`; const v = t(k); return v !== k ? v : tool.display_name })()}</span>
                    <p className="text-xs text-muted-foreground">{(() => { const k = `builtinTool.toolDesc_${tool.name}`; const v = t(k); return v !== k ? v : tool.description })()}</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={toggles[tool.name] ?? false}
                    onChange={(e) => setToggles(prev => ({ ...prev, [tool.name]: e.target.checked }))}
                    className="rounded border-input h-4 w-4"
                  />
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    )
  }

  function renderRulesSection(rules: string[], setRules: (v: string[]) => void) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>{t('agent.rules')}</Label>
          <Button type="button" variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setRules([...rules, ''])}>
            + {t('agent.addRule')}
          </Button>
        </div>
        {rules.length > 0 ? (
          <div className="space-y-2 rounded-md border p-3">
            {rules.map((rule, idx) => (
              <div key={idx} className="flex gap-2">
                <Textarea
                  rows={2}
                  value={rule}
                  onChange={(e) => { const next = [...rules]; next[idx] = e.target.value; setRules(next) }}
                  placeholder={t('agent.rulePlaceholder')}
                  className="flex-1 text-sm"
                />
                <Button type="button" variant="ghost" size="sm" className="h-8 px-2 text-destructive shrink-0" onClick={() => setRules(rules.filter((_, i) => i !== idx))}>
                  ✕
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">{t('agent.rulesHint')}</p>
        )}
      </div>
    )
  }

  function renderProviderModelSelects(currentProvider: string, setProvider: (v: string) => void, defaultModel?: string | null) {
    return (
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>{t('agent.llmProvider')}</Label>
          <Select value={currentProvider} onValueChange={setProvider}>
            <SelectTrigger>
              <SelectValue placeholder={t('agent.selectProvider')} />
            </SelectTrigger>
            <SelectContent>
              {providers?.items?.map((p) => (
                <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>{t('agent.modelName')}</Label>
          {(() => {
            const selectedProvider = providers?.items?.find((p) => String(p.id) === currentProvider)
            const modelList = selectedProvider?.models
            if (modelList && modelList.length > 0) {
              return (
                <Select name="model_name" defaultValue={defaultModel ?? undefined}>
                  <SelectTrigger>
                    <SelectValue placeholder={t('agent.selectModel')} />
                  </SelectTrigger>
                  <SelectContent>
                    {modelList.map((m) => (
                      <SelectItem key={m.name} value={m.name}>{m.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )
            }
            return <Input name="model_name" placeholder={t('agent.modelPlaceholder')} defaultValue={defaultModel ?? ''} />
          })()}
        </div>
      </div>
    )
  }

  function renderAdvancedParams(show: boolean, setShow: (v: boolean) => void, paramEnabled: Record<string, boolean>, setParamEnabled: (fn: (p: Record<string, boolean>) => Record<string, boolean>) => void, prefix: string, defaults?: Partial<Agent>) {
    return (
      <>
        <button type="button" onClick={() => setShow(!show)} className="text-sm text-muted-foreground hover:text-foreground">
          {t('agent.advancedParams')} {show ? '▲' : '▼'}
        </button>
        {show && (
          <div className="grid grid-cols-2 gap-4 p-3 rounded-md border bg-muted/30">
            <ParamRow id={`${prefix}-top_p`} label={t('agent.topP')} help={t('agent.topPHelp')} enabled={paramEnabled.top_p ?? false} onToggle={(v) => setParamEnabled(p => ({ ...p, top_p: v }))}>
              <Input name="top_p" type="number" step="0.05" min="0" max="1" defaultValue={defaults?.top_p ?? ''} placeholder="1.0" />
            </ParamRow>
            <ParamRow id={`${prefix}-max_tokens`} label={t('agent.maxTokens')} help={t('agent.maxTokensHelp')} enabled={paramEnabled.max_tokens ?? false} onToggle={(v) => setParamEnabled(p => ({ ...p, max_tokens: v }))}>
              <Input name="max_tokens" type="number" min="1" defaultValue={defaults?.max_tokens ?? ''} placeholder="4096" />
            </ParamRow>
            <ParamRow id={`${prefix}-presence`} label={t('agent.presencePenalty')} help={t('agent.presencePenaltyHelp')} enabled={paramEnabled.presence_penalty ?? false} onToggle={(v) => setParamEnabled(p => ({ ...p, presence_penalty: v }))}>
              <Input name="presence_penalty" type="number" step="0.1" min="-2" max="2" defaultValue={defaults?.presence_penalty ?? ''} placeholder="0" />
            </ParamRow>
            <ParamRow id={`${prefix}-frequency`} label={t('agent.frequencyPenalty')} help={t('agent.frequencyPenaltyHelp')} enabled={paramEnabled.frequency_penalty ?? false} onToggle={(v) => setParamEnabled(p => ({ ...p, frequency_penalty: v }))}>
              <Input name="frequency_penalty" type="number" step="0.1" min="-2" max="2" defaultValue={defaults?.frequency_penalty ?? ''} placeholder="0" />
            </ParamRow>
          </div>
        )}
      </>
    )
  }

  function renderSubAgentsToggle(checked: boolean, onChange: (v: boolean) => void) {
    return (
      <div className="flex items-center justify-between rounded-md border p-3">
        <div>
          <span className="text-sm font-medium">{t('agent.enableSubAgents')}</span>
          <p className="text-xs text-muted-foreground">{t('agent.enableSubAgentsHelp')}</p>
        </div>
        <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="rounded border-input h-4 w-4" />
      </div>
    )
  }

  return (
    <div className={cn("flex flex-col flex-1", !embedded && "overflow-hidden")}>
      <div className={cn("overflow-auto flex-1", embedded ? "p-4" : "p-6")}>
      {!embedded && (
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">{t('agent.title')}</h1>
          <Button onClick={() => setOpen(true)}>{t('agent.createAgent')}</Button>
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent className="max-w-lg max-h-[85vh] flex flex-col">
            <DialogHeader>
              <DialogTitle>{t('agent.createAgent')}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4 flex-1 overflow-y-auto pr-1">
              <div className="space-y-2">
                <Label htmlFor="name">{t('common.name')}</Label>
                <Input id="name" name="name" required placeholder={t('agent.agentName')} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">{t('project.description')}</Label>
                <Input id="description" name="description" placeholder={t('agent.descriptionPlaceholder')} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="system_prompt">{t('agent.systemPrompt')}</Label>
                <Textarea id="system_prompt" name="system_prompt" rows={4} placeholder={t('agent.systemPromptPlaceholder')} />
              </div>
              {renderRulesSection(createRules, setCreateRules)}
              {renderProviderModelSelects(providerType, setProviderType)}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5">
                    <Label htmlFor="temperature">{t('agent.temperature')}</Label>
                    <TooltipProvider delayDuration={200}>
                      <Tooltip>
                        <TooltipTrigger asChild><HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" /></TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs text-xs">{t('agent.temperatureHelp')}</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                  <Input id="temperature" name="temperature" type="number" step="0.1" min="0" max="2" defaultValue="0.7" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="visibility">{t('agent.visibility')}</Label>
                  <select name="visibility" id="visibility" defaultValue="private" className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm">
                    <option value="private">{t('agent.visibilityPrivate')}</option>
                    <option value="public">{t('agent.visibilityPublic')}</option>
                  </select>
                </div>
              </div>
              {renderAdvancedParams(showAdvanced, setShowAdvanced, createParamEnabled, setCreateParamEnabled, 'c')}
              {renderBuiltinToolsSection(createBuiltinTools, setCreateBuiltinTools)}
              {renderSubAgentsToggle(createSubAgents, setCreateSubAgents)}
              <Button type="submit" className="w-full" disabled={createMutation.isPending}>
                {createMutation.isPending ? t('common.loading') : t('common.create')}
              </Button>
            </form>
          </DialogContent>
        </Dialog>

      <Dialog open={editOpen} onOpenChange={(o) => { setEditOpen(o); if (!o) setEditingAgent(null) }}>
        <DialogContent className="max-w-lg max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>{t('agent.editAgent')}</DialogTitle>
          </DialogHeader>
          {editingAgent && (
            <form onSubmit={handleEdit} className="space-y-4 flex-1 overflow-y-auto pr-1">
              <div className="space-y-2">
                <Label htmlFor="edit-name">{t('common.name')}</Label>
                <Input id="edit-name" name="name" required defaultValue={editingAgent.name} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-description">{t('project.description')}</Label>
                <Input id="edit-description" name="description" defaultValue={editingAgent.description ?? ''} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-system_prompt">{t('agent.systemPrompt')}</Label>
                <Textarea id="edit-system_prompt" name="system_prompt" rows={4} defaultValue={editingAgent.system_prompt ?? ''} />
              </div>
              {renderRulesSection(editRules, setEditRules)}
              {renderProviderModelSelects(editProviderType, setEditProviderType, editingAgent.model_name)}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5">
                    <Label htmlFor="edit-temperature">{t('agent.temperature')}</Label>
                    <TooltipProvider delayDuration={200}>
                      <Tooltip>
                        <TooltipTrigger asChild><HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" /></TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs text-xs">{t('agent.temperatureHelp')}</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                  <Input id="edit-temperature" name="temperature" type="number" step="0.1" min="0" max="2" defaultValue={editingAgent.temperature} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-visibility">{t('agent.visibility')}</Label>
                  <select name="visibility" id="edit-visibility" defaultValue={editingAgent.visibility} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm">
                    <option value="private">{t('agent.visibilityPrivate')}</option>
                    <option value="public">{t('agent.visibilityPublic')}</option>
                  </select>
                </div>
              </div>
              {renderAdvancedParams(showEditAdvanced, setShowEditAdvanced, editParamEnabled, setEditParamEnabled, 'e', editingAgent)}
              {renderBuiltinToolsSection(editBuiltinTools, setEditBuiltinTools)}
              {renderSubAgentsToggle(editSubAgents, setEditSubAgents)}
              <div className="flex gap-2">
                <Button type="submit" className="flex-1" disabled={updateMutation.isPending}>
                  {updateMutation.isPending ? t('common.saving') : t('common.save')}
                </Button>
                <Button type="button" variant="destructive" onClick={() => setDeleteTarget(editingAgent)}>
                  {t('common.delete')}
                </Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">{t('common.loading')}</div>
      ) : isError ? (
        <div className="text-center py-12 text-destructive">{t('error.loadFailed')}</div>
      ) : !items.length ? (
        <div className="text-center py-12 text-muted-foreground">{t('agent.emptyHint')}</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((agent) => (
            <Card key={agent.id} className="cursor-pointer hover:bg-accent/50 transition-colors" onClick={() => openEditDialog(agent)}>
              <CardHeader className="pb-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap min-w-0">
                    <CardTitle className="text-base truncate">{agent.name}</CardTitle>
                    {agent.visibility === 'public' && <Badge variant="secondary">{t('agent.visibilityPublic')}</Badge>}
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1"
                      onClick={(e) => { e.stopPropagation(); cloneMutation.mutate(agent.id) }}
                      disabled={cloneMutation.isPending}
                    >
                      <Copy className="h-3.5 w-3.5" />
                      {t('common.clone')}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0 space-y-1">
                {agent.description && <p className="text-sm text-muted-foreground">{agent.description}</p>}
                <div className="flex gap-4 text-xs text-muted-foreground">
                  {agent.model_name && <span>{t('agent.model')}: {agent.model_name}</span>}
                  <span>{t('agent.temperature')}: {agent.temperature}</span>
                </div>
                {(agent.builtin_tools && Object.entries(agent.builtin_tools).some(([, v]) => v?.enabled) || agent.enable_sub_agents || (agent.rules && agent.rules.length > 0)) && (
                  <div className="flex gap-1 flex-wrap pt-1">
                    {agent.builtin_tools && Object.entries(agent.builtin_tools).filter(([, v]) => v?.enabled).map(([name]) => (
                      <Badge key={name} variant="secondary" className="text-xs">
                        {(() => { const k = `builtinTool.tool_${name}`; const v = t(k); return v !== k ? v : (builtinTools?.find(bt => bt.name === name)?.display_name || name) })()}
                      </Badge>
                    ))}
                    {agent.rules && agent.rules.length > 0 && (
                      <Badge variant="secondary" className="text-xs">{t('agent.rules')} ({agent.rules.length})</Badge>
                    )}
                    {agent.enable_sub_agents && (
                      <Badge variant="secondary" className="text-xs">{t('agent.enableSubAgents')}</Badge>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <DeleteConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => { if (!o) setDeleteTarget(null) }}
        itemName={deleteTarget?.name ?? ''}
        descriptionKey="agent.confirmDelete"
        onConfirm={() => {
          if (deleteTarget) {
            deleteMutation.mutate(deleteTarget.id)
            setEditOpen(false)
            setEditingAgent(null)
          }
          setDeleteTarget(null)
        }}
      />

    </div>
    </div>
  )
}
