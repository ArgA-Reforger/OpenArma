'use client'

import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useI18n } from '@/lib/i18n'
import type { Node } from '@xyflow/react'

interface Agent {
  id: number | string
  name: string
  model_name: string | null
}

interface KnowledgeBase {
  id: number | string
  name: string
}

interface MCPTool {
  id: number | string
  name: string
  description: string | null
}

interface NodeInspectorProps {
  node: Node | null
  agents: Agent[]
  knowledgeBases: KnowledgeBase[]
  mcpTools: MCPTool[]
  onUpdate: (nodeId: string, data: Record<string, unknown>) => void
}

export function NodeInspector({ node, agents, knowledgeBases, mcpTools, onUpdate }: NodeInspectorProps) {
  const { t } = useI18n()

  if (!node) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        {t('topology.selectNode')}
      </div>
    )
  }

  const data = node.data as Record<string, unknown>

  function update(key: string, value: unknown) {
    onUpdate(node!.id, { ...data, [key]: value })
  }

  function updateConfig(key: string, value: unknown) {
    const config = (data.config as Record<string, unknown>) || {}
    onUpdate(node!.id, { ...data, config: { ...config, [key]: value } })
  }

  return (
    <div className="p-4 space-y-4 overflow-auto">
      <h3 className="font-semibold text-sm">{t('topology.nodeConfig')}</h3>

      <div className="space-y-2">
        <Label className="text-xs">{t('topology.nodeLabel')}</Label>
        <Input
          value={(data.label as string) || ''}
          onChange={(e) => update('label', e.target.value)}
          className="h-8 text-sm"
        />
      </div>

      {node.type === 'agent' && (
        <div className="space-y-2">
          <Label className="text-xs">{t('topology.selectAgent')}</Label>
          <select
            value={data.agentId != null ? String(data.agentId) : ''}
            onChange={(e) => {
              const val = e.target.value
              if (!val) return
              const agent = agents.find((a) => String(a.id) === val)
              const defaultLabel = t('topology.node_agent')
              const patch: Record<string, unknown> = {
                ...data,
                agentId: val,
                agentName: agent?.name || '',
                modelName: agent?.model_name || '',
              }
              if (!data.label || data.label === defaultLabel || data.label === 'Agent') {
                patch.label = agent?.name || data.label
              }
              onUpdate(node!.id, patch)
            }}
            className="flex h-8 w-full rounded-md border border-input bg-transparent px-2 text-sm"
          >
            <option value="">{t('topology.chooseAgent')}</option>
            {agents.map((a) => (
              <option key={String(a.id)} value={String(a.id)}>
                {a.name} {a.model_name ? `(${a.model_name})` : ''}
              </option>
            ))}
          </select>
        </div>
      )}

      {(node.type === 'coordinator' || node.type === 'aggregator') && (
        <>
          <div className="space-y-2">
            <Label className="text-xs">{t('topology.mergeStrategy')}</Label>
            <select
              value={((data.config as Record<string, unknown>)?.merge_strategy as string) || node.type}
              onChange={(e) => updateConfig('merge_strategy', e.target.value)}
              className="flex h-8 w-full rounded-md border border-input bg-transparent px-2 text-sm"
            >
              <option value="coordinator">{t('topology.strategyCoordinator')}</option>
              <option value="aggregator">{t('topology.strategyAggregator')}</option>
              <option value="passthrough">{t('topology.strategyPassthrough')}</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label className="text-xs">{t('topology.customPrompt')}</Label>
            <Textarea
              value={((data.config as Record<string, unknown>)?.system_prompt as string) || ''}
              onChange={(e) => updateConfig('system_prompt', e.target.value)}
              rows={3}
              className="text-sm"
              placeholder={t('topology.customPromptHint')}
            />
          </div>
        </>
      )}

      {node.type === 'condition' && (
        <div className="space-y-2">
          <Label className="text-xs">{t('topology.conditionExpr')}</Label>
          <Textarea
            value={((data.config as Record<string, unknown>)?.expression as string) || ''}
            onChange={(e) => updateConfig('expression', e.target.value)}
            rows={3}
            className="text-sm"
            placeholder={t('topology.conditionHint')}
          />
        </div>
      )}

      {node.type === 'tool' && (
        <div className="space-y-2">
          <Label className="text-xs">{t('topology.selectTool')}</Label>
          <select
            value={((data.config as Record<string, unknown>)?.tool_name as string) || ''}
            onChange={(e) => {
              const config = (data.config as Record<string, unknown>) || {}
              const patch: Record<string, unknown> = {
                ...data,
                config: { ...config, tool_name: e.target.value },
                toolName: e.target.value,
              }
              const defaultToolLabel = t('topology.node_tool')
              if (!data.label || data.label === defaultToolLabel || data.label === 'Tool') {
                patch.label = e.target.value
              }
              onUpdate(node!.id, patch)
            }}
            className="flex h-8 w-full rounded-md border border-input bg-transparent px-2 text-sm"
          >
            <option value="">{t('topology.chooseTool')}</option>
            {mcpTools.map((tool) => (
              <option key={tool.id} value={tool.name}>
                {tool.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {node.type === 'rag' && (
        <>
          <div className="space-y-2">
            <Label className="text-xs">{t('topology.selectKB')}</Label>
            <div className="space-y-1 max-h-32 overflow-auto">
              {knowledgeBases.map((kb) => {
                const kbIds = ((data.config as Record<string, unknown>)?.kb_ids as (number | string)[]) || []
                const kbIdStr = String(kb.id)
                const checked = kbIds.some((id) => String(id) === kbIdStr)
                return (
                  <label key={String(kb.id)} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => {
                        const next = checked ? kbIds.filter((id) => String(id) !== kbIdStr) : [...kbIds, kbIdStr]
                        updateConfig('kb_ids', next)
                      }}
                      className="rounded"
                    />
                    {kb.name}
                  </label>
                )
              })}
            </div>
          </div>
          <div className="space-y-2">
            <Label className="text-xs">{t('topology.topK')}</Label>
            <Input
              type="number"
              min={1}
              max={20}
              value={((data.config as Record<string, unknown>)?.top_k as number) || 5}
              onChange={(e) => updateConfig('top_k', Number(e.target.value))}
              className="h-8 text-sm"
            />
          </div>
        </>
      )}

      <div className="pt-2 border-t">
        <p className="text-[10px] text-muted-foreground">
          ID: {node.id} | Type: {node.type}
        </p>
      </div>
    </div>
  )
}
