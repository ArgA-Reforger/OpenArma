'use client'

import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import {
  Bot, GitMerge, Layers, GitBranch, Wrench, BookOpen,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'

const handleStyle = { width: 8, height: 8 }

interface AgentNodeData {
  label: string
  agentId?: number
  agentName?: string
  modelName?: string
  [key: string]: unknown
}

export const AgentNode = memo(function AgentNode({ data, selected }: NodeProps) {
  const d = data as unknown as AgentNodeData
  return (
    <div className={`rounded-lg border-2 bg-card px-4 py-3 min-w-[160px] shadow-sm transition-colors ${selected ? 'border-primary' : 'border-border'}`}>
      <Handle type="target" position={Position.Top} style={handleStyle} />
      <div className="flex items-center gap-2 mb-1">
        <Bot className="h-4 w-4 text-blue-500 shrink-0" />
        <span className="font-medium text-sm truncate">{d.agentName || d.label || 'Agent'}</span>
      </div>
      {d.modelName && (
        <p className="text-xs text-muted-foreground truncate">{d.modelName}</p>
      )}
      <Handle type="source" position={Position.Bottom} style={handleStyle} />
    </div>
  )
})

interface CoordinatorNodeData {
  label: string
  mergeStrategy?: string
  [key: string]: unknown
}

export const CoordinatorNode = memo(function CoordinatorNode({ data, selected }: NodeProps) {
  const d = data as unknown as CoordinatorNodeData
  return (
    <div className={`rounded-lg border-2 bg-card px-4 py-3 min-w-[160px] shadow-sm transition-colors ${selected ? 'border-primary' : 'border-purple-400'}`}>
      <Handle type="target" position={Position.Top} style={handleStyle} />
      <div className="flex items-center gap-2 mb-1">
        <GitMerge className="h-4 w-4 text-purple-500 shrink-0" />
        <span className="font-medium text-sm">{d.label || 'Coordinator'}</span>
      </div>
      <Badge variant="outline" className="text-[10px]">
        {d.mergeStrategy || 'coordinator'}
      </Badge>
      <Handle type="source" position={Position.Bottom} style={handleStyle} />
    </div>
  )
})

interface AggregatorNodeData {
  label: string
  mergeStrategy?: string
  [key: string]: unknown
}

export const AggregatorNode = memo(function AggregatorNode({ data, selected }: NodeProps) {
  const d = data as unknown as AggregatorNodeData
  return (
    <div className={`rounded-lg border-2 bg-card px-4 py-3 min-w-[160px] shadow-sm transition-colors ${selected ? 'border-primary' : 'border-orange-400'}`}>
      <Handle type="target" position={Position.Top} style={handleStyle} />
      <div className="flex items-center gap-2 mb-1">
        <Layers className="h-4 w-4 text-orange-500 shrink-0" />
        <span className="font-medium text-sm">{d.label || 'Aggregator'}</span>
      </div>
      <Badge variant="outline" className="text-[10px]">
        {d.mergeStrategy || 'aggregator'}
      </Badge>
      <Handle type="source" position={Position.Bottom} style={handleStyle} />
    </div>
  )
})

interface ConditionNodeData {
  label: string
  expression?: string
  [key: string]: unknown
}

export const ConditionNode = memo(function ConditionNode({ data, selected }: NodeProps) {
  const d = data as unknown as ConditionNodeData
  return (
    <div className={`rounded-lg border-2 bg-card px-4 py-3 min-w-[140px] shadow-sm transition-colors ${selected ? 'border-primary' : 'border-yellow-400'}`} style={{ transform: 'rotate(0deg)' }}>
      <Handle type="target" position={Position.Top} style={handleStyle} />
      <div className="flex items-center gap-2 mb-1">
        <GitBranch className="h-4 w-4 text-yellow-500 shrink-0" />
        <span className="font-medium text-sm">{d.label || 'Condition'}</span>
      </div>
      {d.expression && (
        <p className="text-[10px] text-muted-foreground truncate max-w-[140px]">{d.expression}</p>
      )}
      <Handle type="source" position={Position.Bottom} style={handleStyle} />
    </div>
  )
})

interface ToolNodeData {
  label: string
  toolName?: string
  toolType?: string
  [key: string]: unknown
}

export const ToolNode = memo(function ToolNode({ data, selected }: NodeProps) {
  const d = data as unknown as ToolNodeData
  return (
    <div className={`rounded-lg border-2 bg-card px-4 py-3 min-w-[140px] shadow-sm transition-colors ${selected ? 'border-primary' : 'border-green-400'}`}>
      <Handle type="target" position={Position.Top} style={handleStyle} />
      <div className="flex items-center gap-2 mb-1">
        <Wrench className="h-4 w-4 text-green-500 shrink-0" />
        <span className="font-medium text-sm">{d.label || 'Tool'}</span>
      </div>
      {d.toolName && (
        <p className="text-xs text-muted-foreground truncate">{d.toolName}</p>
      )}
      <Handle type="source" position={Position.Bottom} style={handleStyle} />
    </div>
  )
})

interface RAGNodeData {
  label: string
  kbIds?: number[]
  topK?: number
  [key: string]: unknown
}

export const RAGNode = memo(function RAGNode({ data, selected }: NodeProps) {
  const d = data as unknown as RAGNodeData
  return (
    <div className={`rounded-lg border-2 bg-card px-4 py-3 min-w-[140px] shadow-sm transition-colors ${selected ? 'border-primary' : 'border-teal-400'}`}>
      <Handle type="target" position={Position.Top} style={handleStyle} />
      <div className="flex items-center gap-2 mb-1">
        <BookOpen className="h-4 w-4 text-teal-500 shrink-0" />
        <span className="font-medium text-sm">{d.label || 'RAG'}</span>
      </div>
      {d.kbIds && d.kbIds.length > 0 && (
        <p className="text-[10px] text-muted-foreground">{d.kbIds.length} KB(s)</p>
      )}
      <Handle type="source" position={Position.Bottom} style={handleStyle} />
    </div>
  )
})

export const nodeTypes = {
  agent: AgentNode,
  coordinator: CoordinatorNode,
  aggregator: AggregatorNode,
  condition: ConditionNode,
  tool: ToolNode,
  rag: RAGNode,
}
