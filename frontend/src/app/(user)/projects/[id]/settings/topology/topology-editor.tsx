'use client'

import { useCallback, useRef, useState, useMemo } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Edge,
  type Node,
  type OnConnect,
  ReactFlowProvider,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import {
  Bot, GitMerge, Layers, GitBranch, Wrench, BookOpen,
  Save, RotateCcw, CheckCircle, Trash2, HelpCircle,
} from 'lucide-react'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { useQuery } from '@tanstack/react-query'
import { nodeTypes } from './node-types'
import { NodeInspector } from './node-inspector'

interface TopologyEditorProps {
  initialTopology: TopologyData | null
  onSave: (topology: TopologyData) => void
}

export interface TopologyData {
  nodes: TopologyNodeDef[]
  edges: TopologyEdgeDef[]
}

interface TopologyNodeDef {
  id: string
  type: string
  agent_id?: number | string
  config: Record<string, unknown>
  position: { x: number; y: number }
}

interface TopologyEdgeDef {
  id: string
  source: string
  target: string
  config: Record<string, unknown>
}

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

interface PageData<T> { items: T[]; total: number }

const NODE_PALETTE = [
  { type: 'agent', icon: Bot, color: 'text-blue-500', label: 'Agent' },
  { type: 'coordinator', icon: GitMerge, color: 'text-purple-500', label: 'Coordinator' },
  { type: 'aggregator', icon: Layers, color: 'text-orange-500', label: 'Aggregator' },
  { type: 'condition', icon: GitBranch, color: 'text-yellow-500', label: 'Condition' },
  { type: 'tool', icon: Wrench, color: 'text-green-500', label: 'Tool' },
  { type: 'rag', icon: BookOpen, color: 'text-teal-500', label: 'RAG' },
] as const

let nodeIdCounter = 0

function toFlowNodes(defs: TopologyNodeDef[]): Node[] {
  return defs.map((n) => ({
    id: n.id,
    type: n.type,
    position: n.position || { x: 0, y: 0 },
    data: {
      label: (n.config as Record<string, unknown>)?.label || n.type,
      agentId: n.agent_id != null ? String(n.agent_id) : undefined,
      agentName: (n.config as Record<string, unknown>)?.agent_name || '',
      modelName: (n.config as Record<string, unknown>)?.model_name || '',
      mergeStrategy: (n.config as Record<string, unknown>)?.merge_strategy || n.type,
      expression: (n.config as Record<string, unknown>)?.expression || '',
      toolName: (n.config as Record<string, unknown>)?.tool_name || '',
      kbIds: (n.config as Record<string, unknown>)?.kb_ids || [],
      topK: (n.config as Record<string, unknown>)?.top_k || 5,
      config: n.config,
    },
  }))
}

function toFlowEdges(defs: TopologyEdgeDef[]): Edge[] {
  return defs.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    animated: true,
    style: { strokeWidth: 2 },
  }))
}

function toTopologyData(nodes: Node[], edges: Edge[]): TopologyData {
  return {
    nodes: nodes.map((n) => {
      const data = n.data as Record<string, unknown>
      const config = (data.config as Record<string, unknown>) || {}
      return {
        id: n.id,
        type: n.type || 'agent',
        agent_id: (data.agentId as number | string | undefined) || undefined,
        config: {
          ...config,
          label: data.label,
          agent_name: data.agentName,
          model_name: data.modelName,
          merge_strategy: data.mergeStrategy,
          expression: data.expression,
          tool_name: data.toolName,
          kb_ids: data.kbIds,
          top_k: data.topK,
        },
        position: n.position,
      }
    }),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      config: {},
    })),
  }
}

function InnerEditor({ initialTopology, onSave }: TopologyEditorProps) {
  const { t } = useI18n()
  const apiClient = useApi()
  const reactFlowWrapper = useRef<HTMLDivElement>(null)

  const initNodes = useMemo(() => initialTopology ? toFlowNodes(initialTopology.nodes) : [], [initialTopology])
  const initEdges = useMemo(() => initialTopology ? toFlowEdges(initialTopology.edges) : [], [initialTopology])

  const [nodes, setNodes, onNodesChange] = useNodesState(initNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initEdges)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)

  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: () => apiClient.get<PageData<Agent>>('/agents'),
  })

  const { data: kbData } = useQuery({
    queryKey: ['knowledge-bases'],
    queryFn: () => apiClient.get<PageData<KnowledgeBase>>('/knowledge-bases'),
  })

  const { data: toolsData } = useQuery({
    queryKey: ['mcp-tools-all'],
    queryFn: async () => {
      try {
        const servers = await apiClient.get<PageData<{ id: number }>>('/mcp-servers')
        const tools: MCPTool[] = []
        for (const s of servers.items || []) {
          try {
            const detail = await apiClient.get<{ tools?: MCPTool[] }>(`/mcp-servers/${s.id}`)
            if (detail.tools) tools.push(...detail.tools)
          } catch { /* skip */ }
        }
        return tools
      } catch { return [] }
    },
  })

  const agents = agentsData?.items ?? []
  const knowledgeBases = kbData?.items ?? []
  const mcpTools = toolsData || []

  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({ ...connection, animated: true, style: { strokeWidth: 2 } }, eds))
    },
    [setEdges],
  )

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode({ ...node, data: { ...node.data } })
  }, [])

  const onPaneClick = useCallback(() => {
    setSelectedNode(null)
  }, [])

  function handleDragStart(e: React.DragEvent, nodeType: string) {
    e.dataTransfer.setData('application/reactflow', nodeType)
    e.dataTransfer.effectAllowed = 'move'
  }

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      const type = e.dataTransfer.getData('application/reactflow')
      if (!type) return

      const wrapper = reactFlowWrapper.current
      if (!wrapper) return

      const bounds = wrapper.getBoundingClientRect()
      const position = {
        x: e.clientX - bounds.left - 80,
        y: e.clientY - bounds.top - 20,
      }

      nodeIdCounter += 1
      const id = `${type}_${Date.now()}_${nodeIdCounter}`

      const label = t(`topology.node_${type}`)

      const newNode: Node = {
        id,
        type,
        position,
        data: {
          label,
          config: {},
          agentId: undefined,
          agentName: '',
          modelName: '',
          mergeStrategy: type === 'coordinator' || type === 'aggregator' ? type : '',
          expression: '',
          toolName: '',
          kbIds: [],
          topK: 5,
        },
      }

      setNodes((nds) => [...nds, newNode])
    },
    [setNodes, t],
  )

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }, [])

  function handleNodeUpdate(nodeId: string, newData: Record<string, unknown>) {
    setNodes((nds) =>
      nds.map((n) => (n.id === nodeId ? { ...n, data: newData } : n)),
    )
    setSelectedNode((prev) => {
      if (!prev || prev.id !== nodeId) return prev
      return { ...prev, data: newData }
    })
  }

  function handleDeleteSelected() {
    if (!selectedNode) return
    setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id))
    setEdges((eds) => eds.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id))
    setSelectedNode(null)
  }

  function localizeError(err: string): string {
    if (err.includes('at least one node')) return t('topology.errNoNodes')
    if (err.includes('missing agent_id')) return t('topology.errMissingAgent')
    if (err.includes('contains cycles')) return t('topology.errCycle')
    if (err.includes('No root nodes')) return t('topology.errNoRoot')
    if (err.includes('No leaf')) return t('topology.errNoLeaf')
    if (err.includes('not bound to project')) return t('topology.errUnboundAgent')
    if (err.includes('invalid type')) return t('topology.errInvalidType')
    if (err.includes('Self-loop')) return t('topology.errSelfLoop')
    return err
  }

  function handleValidate() {
    const topo = toTopologyData(nodes, edges)
    const errs: string[] = []
    if (topo.nodes.length === 0) errs.push(localizeError('at least one node'))
    for (const n of topo.nodes) {
      if (n.type === 'agent' && !n.agent_id) errs.push(localizeError('missing agent_id'))
      if (topo.edges.some((e) => e.source === n.id && e.target === n.id)) errs.push(localizeError('Self-loop'))
    }
    if (errs.length === 0) {
      toast.success(t('topology.validationPassed'))
    } else {
      toast.error(errs.join('\n'))
    }
  }

  function handleSave() {
    const topo = toTopologyData(nodes, edges)
    onSave(topo)
  }

  function handleReset() {
    setNodes(initNodes)
    setEdges(initEdges)
    setSelectedNode(null)
  }

  return (
    <div className="flex h-full min-h-[400px] border rounded-lg overflow-hidden">
      {/* Left: Node Palette */}
      <div className="w-48 border-r bg-muted/30 p-3 space-y-2 shrink-0">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            {t('topology.nodePalette')}
          </h3>
          <a href="/tutorial#topology-nodes" target="_blank" rel="noopener noreferrer" title={t('topology.nodeHelp')}>
            <HelpCircle className="h-3.5 w-3.5 text-muted-foreground hover:text-primary transition-colors" />
          </a>
        </div>
        {NODE_PALETTE.map((item) => {
          const Icon = item.icon
          return (
            <div
              key={item.type}
              draggable
              onDragStart={(e) => handleDragStart(e, item.type)}
              className="flex items-center gap-2 px-3 py-2 rounded-md border bg-card cursor-grab hover:border-primary transition-colors text-sm"
              title={t(`topology.nodeHint_${item.type}`)}
            >
              <Icon className={`h-4 w-4 ${item.color} shrink-0`} />
              <span>{t(`topology.node_${item.type}`)}</span>
            </div>
          )
        })}
      </div>

      {/* Center: Canvas */}
      <div className="flex-1 relative" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={nodeTypes}
          fitView
          deleteKeyCode="Delete"
          className="bg-background"
        >
          <Background gap={16} size={1} />
          <Controls />
          <MiniMap
            nodeStrokeWidth={3}
            className="!bg-muted/50"
          />
        </ReactFlow>

        {/* Toolbar */}
        <div className="absolute top-3 right-3 flex gap-2 z-10">
          {selectedNode && (
            <Button size="sm" variant="destructive" onClick={handleDeleteSelected}>
              <Trash2 className="h-4 w-4 mr-1" />{t('common.delete')}
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={handleReset}>
            <RotateCcw className="h-4 w-4 mr-1" />{t('topology.reset')}
          </Button>
          <Button size="sm" variant="outline" onClick={handleValidate}>
            <CheckCircle className="h-4 w-4 mr-1" />{t('topology.validate')}
          </Button>
          <Button size="sm" onClick={handleSave}>
            <Save className="h-4 w-4 mr-1" />{t('common.save')}
          </Button>
        </div>
      </div>

      {/* Right: Inspector */}
      <div className="w-64 border-l bg-muted/30 shrink-0 overflow-auto">
        <NodeInspector
          node={selectedNode}
          agents={agents}
          knowledgeBases={knowledgeBases}
          mcpTools={mcpTools}
          onUpdate={handleNodeUpdate}
        />
      </div>
    </div>
  )
}

export default function TopologyEditor(props: TopologyEditorProps) {
  return (
    <ReactFlowProvider>
      <InnerEditor {...props} />
    </ReactFlowProvider>
  )
}
