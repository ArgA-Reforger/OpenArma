'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
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
import { cn } from '@/lib/utils'
import { Upload, Trash2, RefreshCw, Copy } from 'lucide-react'
import { useResourceCRUD } from '@/hooks/use-resource-crud'
import { DeleteConfirmDialog } from '@/components/resource/delete-confirm-dialog'
import type { EmbeddedProps, PageData, LLMProviderBase } from '@/types/resources'

interface KnowledgeBase {
  id: number
  name: string
  description: string | null
  embedding_model: string
  chunk_size: number
  chunk_overlap: number
  document_count: number
  status: string
  created_time: string
}

interface KnowledgeDocument {
  id: number
  knowledge_base_id: number
  title: string
  source_type: string
  file_path: string | null
  file_size: number | null
  content: string | null
  chunk_count: number
  status: string
  error_message: string | null
  created_time: string
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useI18n()
  const labels: Record<string, string> = {
    ready: t('knowledge.statusReady'),
    processing: t('knowledge.statusProcessing'),
    error: t('knowledge.statusError'),
    pending: t('knowledge.statusPending'),
  }
  const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
    ready: 'default',
    processing: 'secondary',
    error: 'destructive',
    pending: 'outline',
  }
  return <Badge variant={variants[status] ?? 'outline'}>{labels[status] ?? status}</Badge>
}

export function KnowledgePage({ embedded, addDialogOpen, onAddDialogOpenChange }: EmbeddedProps = {}) {
  const api = useApi()
  const { t } = useI18n()
  const [internalOpen, setInternalOpen] = useState(false)
  const open = addDialogOpen ?? internalOpen
  const setOpen = onAddDialogOpenChange ?? setInternalOpen
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeBase | null>(null)
  const [embeddingProvider, setEmbeddingProvider] = useState('')
  const [embeddingModel, setEmbeddingModel] = useState('')
  const [editTarget, setEditTarget] = useState<KnowledgeBase | null>(null)
  const [editName, setEditName] = useState('')
  const [editDescription, setEditDescription] = useState('')

  const {
    items, isLoading, isError,
    createMutation, updateMutation, deleteMutation, cloneMutation,
  } = useResourceCRUD<KnowledgeBase>({
    endpoint: '/knowledge-bases',
    queryKey: ['knowledge-bases'],
    toastKeys: { created: 'knowledge.created', updated: 'knowledge.updated', deleted: 'knowledge.deleted', cloned: 'common.cloneSuccess' },
  })

  const { data: providers } = useQuery({
    queryKey: ['llm-providers'],
    queryFn: () => api.get<PageData<LLMProviderBase>>('/llm-providers'),
  })

  function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    if (!embeddingModel) {
      toast.error(t('knowledge.selectEmbeddingModelRequired'))
      return
    }
    createMutation.mutate({
      name: fd.get('name') as string,
      description: (fd.get('description') as string) || undefined,
      embedding_model: embeddingModel,
      chunk_size: Number(fd.get('chunk_size')) || 512,
      chunk_overlap: Number(fd.get('chunk_overlap')) || 50,
    }, { onSuccess: () => { setOpen(false); setEmbeddingProvider(''); setEmbeddingModel('') } })
  }

  return (
    <div className={cn("flex flex-col flex-1", !embedded && "overflow-hidden")}>
      <div className={cn("overflow-auto flex-1", embedded ? "p-4" : "p-6")}>
      {!embedded && (
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">{t('knowledge.title')}</h1>
          <Button onClick={() => setOpen(true)}>{t('knowledge.createKB')}</Button>
        </div>
      )}

      <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) { setEmbeddingProvider(''); setEmbeddingModel('') } }}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t('knowledge.createKB')}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">{t('knowledge.kbName')}</Label>
                <Input id="name" name="name" required placeholder={t('knowledge.namePlaceholder')} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">{t('knowledge.description')}</Label>
                <Input id="description" name="description" placeholder={t('knowledge.descriptionPlaceholder')} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="chunk_size">{t('knowledge.chunkSize')}</Label>
                  <Input id="chunk_size" name="chunk_size" type="number" defaultValue="512" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="chunk_overlap">{t('knowledge.chunkOverlap')}</Label>
                  <Input id="chunk_overlap" name="chunk_overlap" type="number" defaultValue="50" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>{t('agent.llmProvider')}</Label>
                  <Select value={embeddingProvider} onValueChange={(v) => { setEmbeddingProvider(v); setEmbeddingModel('') }}>
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
                  <Label>{t('knowledge.embeddingModel')}</Label>
                  {(() => {
                    const selectedProvider = providers?.items?.find((p) => String(p.id) === embeddingProvider)
                    const modelList = selectedProvider?.models
                    if (modelList && modelList.length > 0) {
                      return (
                        <Select value={embeddingModel} onValueChange={setEmbeddingModel}>
                          <SelectTrigger>
                            <SelectValue placeholder={t('knowledge.selectEmbeddingModel')} />
                          </SelectTrigger>
                          <SelectContent>
                            {modelList.map((m) => (
                              <SelectItem key={m.name} value={m.name}>{m.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )
                    }
                    return <Input value={embeddingModel} onChange={(e) => setEmbeddingModel(e.target.value)} placeholder={t('knowledge.embeddingModelPlaceholder')} />
                  })()}
                </div>
              </div>
              <Button type="submit" className="w-full" disabled={createMutation.isPending}>
                {createMutation.isPending ? t('common.loading') : t('common.create')}
              </Button>
            </form>
          </DialogContent>
        </Dialog>

      {isLoading ? (
        <div className="text-muted-foreground">{t('common.loading')}</div>
      ) : isError ? (
        <div className="text-center py-12 text-destructive">{t('error.loadFailed')}</div>
      ) : !items.length ? (
        <div className="text-center py-12 text-muted-foreground">{t('knowledge.emptyHint')}</div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {items.map((kb) => (
            <Card
              key={kb.id}
              className="cursor-pointer hover:bg-accent/50 transition-colors"
              onClick={() => { setEditTarget(kb); setEditName(kb.name); setEditDescription(kb.description || '') }}
            >
              <CardHeader className="pb-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap min-w-0">
                    <CardTitle className="text-base truncate">{kb.name}</CardTitle>
                    <StatusBadge status={kb.status} />
                    <span className="text-sm text-muted-foreground">
                      {t('knowledge.documentCount')}: {kb.document_count}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0" onClick={(e) => e.stopPropagation()}>
                    <Button variant="outline" size="sm" className="gap-1" onClick={() => cloneMutation.mutate(kb.id)} disabled={cloneMutation.isPending}>
                      <Copy className="h-3.5 w-3.5" />
                      {t('common.clone')}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                {kb.description && <p className="text-sm text-muted-foreground">{kb.description}</p>}
                <div className="flex gap-4 text-xs text-muted-foreground mt-1">
                  <span>{t('knowledge.embeddingModel')}: {kb.embedding_model}</span>
                  <span>{t('knowledge.chunkSize')}: {kb.chunk_size}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={!!editTarget} onOpenChange={(v) => { if (!v) setEditTarget(null) }}>
        <DialogContent className="max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>{t('knowledge.editKB')}</DialogTitle>
          </DialogHeader>
          {editTarget && (
            <div className="space-y-4 flex-1 overflow-y-auto pr-1">
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  updateMutation.mutate({
                    id: editTarget.id,
                    body: { name: editName, description: editDescription || null },
                  }, { onSuccess: () => setEditTarget(null) })
                }}
                className="space-y-4"
              >
                <div className="space-y-2">
                  <Label>{t('knowledge.kbName')}</Label>
                  <Input value={editName} onChange={(e) => setEditName(e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label>{t('knowledge.description')}</Label>
                  <Input value={editDescription} onChange={(e) => setEditDescription(e.target.value)} placeholder={t('knowledge.descriptionPlaceholder')} />
                </div>
                <div className="flex gap-4 text-sm text-muted-foreground">
                  <span>{t('knowledge.embeddingModel')}: {editTarget.embedding_model}</span>
                  <span>{t('knowledge.chunkSize')}: {editTarget.chunk_size}</span>
                  <span>{t('knowledge.chunkOverlap')}: {editTarget.chunk_overlap}</span>
                </div>
                <div className="flex gap-2">
                  <Button type="submit" className="flex-1" disabled={updateMutation.isPending}>
                    {updateMutation.isPending ? t('common.saving') : t('common.save')}
                  </Button>
                  <Button type="button" variant="destructive" onClick={() => setDeleteTarget(editTarget)}>
                    {t('common.delete')}
                  </Button>
                </div>
              </form>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>{t('knowledge.documents')}</Label>
                  <KBUploadButton kbId={editTarget.id} />
                </div>
                <KBDocuments kbId={editTarget.id} />
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <DeleteConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => { if (!o) setDeleteTarget(null) }}
        itemName={deleteTarget?.name ?? ''}
        descriptionKey="knowledge.confirmDelete"
        onConfirm={() => {
          if (deleteTarget) {
            deleteMutation.mutate(deleteTarget.id)
            setEditTarget(null)
          }
          setDeleteTarget(null)
        }}
      />

      </div>
    </div>
  )
}

function KBUploadButton({ kbId }: { kbId: number }) {
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const [sourceType, setSourceType] = useState<'upload' | 'text' | 'url'>('upload')
  const [uploading, setUploading] = useState(false)

  function handleUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const formData = new FormData()
    formData.append('source_type', sourceType)
    formData.append('title', (fd.get('title') as string) || 'Untitled')
    if (sourceType === 'upload') {
      const file = fd.get('file') as File
      if (file?.size) formData.append('file', file)
    } else if (sourceType === 'text') {
      formData.append('content', (fd.get('content') as string) || '')
    } else if (sourceType === 'url') {
      formData.append('url', (fd.get('url') as string) || '')
    }
    setUploading(true)
    api.upload(`/knowledge-bases/${kbId}/documents`, formData)
      .then(() => {
        queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] })
        queryClient.invalidateQueries({ queryKey: ['kb-documents', kbId] })
        setOpen(false)
        toast.success(t('knowledge.uploaded'))
      })
      .catch((err: Error) => toast.error(err.message))
      .finally(() => setUploading(false))
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="ghost"><Upload className="h-4 w-4" /></Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('knowledge.uploadDoc')}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleUpload} className="space-y-4">
          <div className="space-y-2">
            <Label>{t('knowledge.sourceType')}</Label>
            <Select value={sourceType} onValueChange={(v) => setSourceType(v as 'upload' | 'text' | 'url')}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="upload">{t('knowledge.sourceUpload')}</SelectItem>
                <SelectItem value="text">{t('knowledge.sourceText')}</SelectItem>
                <SelectItem value="url">{t('knowledge.sourceUrl')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="doc-title">{t('common.name')}</Label>
            <Input id="doc-title" name="title" placeholder="Document title" />
          </div>
          {sourceType === 'upload' && (
            <div className="space-y-2">
              <Label htmlFor="file">{t('knowledge.uploadFile')}</Label>
              <Input id="file" name="file" type="file" />
            </div>
          )}
          {sourceType === 'text' && (
            <div className="space-y-2">
              <Label htmlFor="content">{t('knowledge.textContent')}</Label>
              <Textarea id="content" name="content" rows={6} placeholder={t('knowledge.textPlaceholder')} />
            </div>
          )}
          {sourceType === 'url' && (
            <div className="space-y-2">
              <Label htmlFor="url">URL</Label>
              <Input id="url" name="url" type="url" placeholder={t('knowledge.urlPlaceholder')} />
            </div>
          )}
          <Button type="submit" disabled={uploading}>{t('knowledge.uploadDoc')}</Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function KBDocuments({ kbId }: { kbId: number }) {
  const api = useApi()
  const queryClient = useQueryClient()
  const { t } = useI18n()
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeDocument | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['kb-documents', kbId],
    queryFn: () => api.get<PageData<KnowledgeDocument>>(`/knowledge-bases/${kbId}/documents`),
  })

  const deleteMutation = useMutation({
    mutationFn: (docId: number) => api.delete(`/knowledge-bases/${kbId}/documents/${docId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kb-documents', kbId] })
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] })
      setDeleteTarget(null)
      toast.success(t('knowledge.docDeleted'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const reprocessMutation = useMutation({
    mutationFn: (docId: number) => api.post(`/knowledge-bases/${kbId}/documents/${docId}/reprocess`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kb-documents', kbId] })
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] })
      toast.success(t('knowledge.reprocessed'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  if (isLoading) return <div className="text-sm text-muted-foreground py-4">{t('common.loading')}</div>
  const docs = data?.items ?? []
  if (!docs.length) return <div className="text-sm text-muted-foreground py-4">{t('knowledge.documents')}: 0</div>

  return (
    <>
      <div className="space-y-2">
        {docs.map((doc) => (
          <div key={doc.id} className="flex items-center justify-between p-3 rounded border text-sm">
            <div className="flex items-center gap-2">
              <span className="font-medium">{doc.title}</span>
              <StatusBadge status={doc.status} />
              <span className="text-muted-foreground">{t('knowledge.chunks')}: {doc.chunk_count}</span>
            </div>
            <div className="flex gap-1">
              <Button size="sm" variant="ghost" onClick={() => reprocessMutation.mutate(doc.id)} disabled={reprocessMutation.isPending}>
                <RefreshCw className="h-4 w-4" />
              </Button>
              <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => setDeleteTarget(doc)}>
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        ))}
      </div>
      <DeleteConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => { if (!o) setDeleteTarget(null) }}
        itemName={deleteTarget?.title ?? ''}
        descriptionKey="knowledge.confirmDeleteDoc"
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
      />
    </>
  )
}
