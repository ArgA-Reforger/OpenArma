'use client'

import { useState, useMemo, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { CardLoadingState } from '@/components/loading-state'
import { EmptyState } from '@/components/empty-state'
import { DeleteConfirmDialog } from '@/components/resource/delete-confirm-dialog'
import { X, Plus, Loader2, CheckCircle2, XCircle, Download } from 'lucide-react'
import type { EmbeddedProps, PageData, ModelEntry } from '@/types/resources'

interface LLMProvider {
  id: number
  name: string
  provider_type: string
  api_base: string | null
  api_key_masked: string | null
  models: ModelEntry[] | null
  rpm_limit: number | null
  tpm_limit: number | null
  is_active: boolean
  created_time: string
}

interface PresetModel {
  name: string
  label: string
  context_length: number
  input_price: number
  output_price: number
}

interface Preset {
  provider_type: string
  label: string
  api_base: string
  currency: string
  models: PresetModel[]
}

function ModelListEditor({
  models,
  onChange,
  placeholder,
  onVerify,
  verifyingModel,
}: {
  models: ModelEntry[]
  onChange: (models: ModelEntry[]) => void
  placeholder: string
  onVerify?: (modelName: string) => void
  verifyingModel?: string | null
}) {
  const [input, setInput] = useState('')

  function addModel() {
    const name = input.trim()
    if (!name || models.some((m) => m.name === name)) return
    onChange([...models, { name, verified_at: null, verified_ok: null }])
    setInput('')
  }

  function formatTime(iso: string | null) {
    if (!iso) return null
    try {
      return new Date(iso).toLocaleString()
    } catch {
      return iso
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addModel() } }}
          className="flex-1"
        />
        <Button type="button" variant="outline" size="sm" onClick={addModel} disabled={!input.trim()}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      {models.length > 0 && (
        <div className="rounded-md border divide-y text-sm">
          {models.map((m) => (
            <div key={m.name} className="flex items-center justify-between px-3 py-2">
              <div className="flex items-center gap-2">
                {m.verified_ok === true && <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />}
                {m.verified_ok === false && <XCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />}
                {m.verified_ok == null && <div className="h-3.5 w-3.5 rounded-full border-2 border-muted-foreground/30 shrink-0" />}
                <span className="font-medium">{m.name}</span>
                {m.verified_at && (
                  <span className="text-xs text-muted-foreground">{formatTime(m.verified_at)}</span>
                )}
                {m.verified_ok == null && (
                  <span className="text-xs text-muted-foreground italic">{/* not verified */}</span>
                )}
              </div>
              <div className="flex items-center gap-1">
                {onVerify && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs"
                    onClick={() => onVerify(m.name)}
                    disabled={verifyingModel === m.name}
                  >
                    {verifyingModel === m.name ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <CheckCircle2 className="h-3 w-3" />
                    )}
                  </Button>
                )}
                <button
                  type="button"
                  onClick={() => onChange(models.filter((x) => x.name !== m.name))}
                  className="rounded-full hover:bg-muted-foreground/20 p-1"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function LLMProvidersPage({ embedded, addDialogOpen, onAddDialogOpenChange }: EmbeddedProps = {}) {
  const api = useApi()
  const queryClient = useQueryClient()
  const [internalOpen, setInternalOpen] = useState(false)
  const open = addDialogOpen ?? internalOpen
  const setOpen = onAddDialogOpenChange ?? setInternalOpen
  const [selectedPreset, setSelectedPreset] = useState<string>('')
  const [apiBase, setApiBase] = useState('')
  const [createModels, setCreateModels] = useState<ModelEntry[]>([])
  const [deleteTarget, setDeleteTarget] = useState<LLMProvider | null>(null)
  const [editTarget, setEditTarget] = useState<LLMProvider | null>(null)
  const [editName, setEditName] = useState('')
  const [editApiBase, setEditApiBase] = useState('')
  const [editApiKey, setEditApiKey] = useState('')
  const [editRpm, setEditRpm] = useState('')
  const [editTpm, setEditTpm] = useState('')
  const [editModels, setEditModels] = useState<ModelEntry[]>([])
  const [verifyingModel, setVerifyingModel] = useState<string | null>(null)
  const [fetchingModels, setFetchingModels] = useState(false)
  const [remoteModels, setRemoteModels] = useState<string[]>([])
  const [remoteSelected, setRemoteSelected] = useState<Set<string>>(new Set())
  const [showRemotePicker, setShowRemotePicker] = useState(false)
  const [remoteVerified, setRemoteVerified] = useState<Record<string, { ok: boolean; at: string }>>({})
  const [remoteVerifying, setRemoteVerifying] = useState<string | null>(null)
  const [createFetchingModels, setCreateFetchingModels] = useState(false)
  const [createVerifyingModel, setCreateVerifyingModel] = useState<string | null>(null)
  const [createRemoteModels, setCreateRemoteModels] = useState<string[]>([])
  const [createRemoteSelected, setCreateRemoteSelected] = useState<Set<string>>(new Set())
  const [showCreateRemotePicker, setShowCreateRemotePicker] = useState(false)
  const [createRemoteVerified, setCreateRemoteVerified] = useState<Record<string, { ok: boolean; at: string }>>({})
  const [createRemoteVerifying, setCreateRemoteVerifying] = useState<string | null>(null)
  const [silentCreatedId, setSilentCreatedId] = useState<number | null>(null)
  const nameRef = useRef<HTMLInputElement>(null)
  const { t } = useI18n()

  const { data: presets } = useQuery<Preset[]>({
    queryKey: ['llm-presets'],
    queryFn: () => api.get('/llm-providers/presets'),
    staleTime: Infinity,
  })

  const presetOptions = useMemo(() => {
    if (!presets) return []
    return presets.map((p, i) => ({
      key: `${p.provider_type}:${i}`,
      label: p.label,
      preset: p,
    }))
  }, [presets])

  const activePreset = useMemo(() => {
    if (!selectedPreset || !presets) return null
    const idx = parseInt(selectedPreset.split(':')[1], 10)
    return presets[idx] ?? null
  }, [selectedPreset, presets])

  useEffect(() => {
    if (activePreset) {
      setApiBase(activePreset.api_base)
      if (nameRef.current && !nameRef.current.value) {
        nameRef.current.value = activePreset.label
      }
    }
  }, [activePreset])

  const { data, isLoading, isError } = useQuery({
    queryKey: ['llm-providers'],
    queryFn: () => api.get<PageData<LLMProvider>>('/llm-providers'),
  })

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post<{ id: number }>('/llm-providers', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llm-providers'] })
      setOpen(false)
      resetCreateForm()
      toast.success(t('llm.added'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  function resetCreateForm() {
    setSelectedPreset('')
    setApiBase('')
    setCreateModels([])
    setSilentCreatedId(null)
    setCreateFetchingModels(false)
    setCreateVerifyingModel(null)
    setCreateRemoteModels([])
    setCreateRemoteSelected(new Set())
    setShowCreateRemotePicker(false)
    setCreateRemoteVerified({})
    setCreateRemoteVerifying(null)
  }

  function getCreateFormBody() {
    const name = nameRef.current?.value || ''
    const apiKeyEl = document.querySelector<HTMLInputElement>('#create_api_key')
    const apiKey = apiKeyEl?.value || ''
    const rpmEl = document.querySelector<HTMLInputElement>('#create_rpm_limit')
    const tpmEl = document.querySelector<HTMLInputElement>('#create_tpm_limit')
    return {
      name,
      provider_type: activePreset?.provider_type || '',
      api_base: apiBase || undefined,
      api_key: apiKey || undefined,
      models: createModels.length > 0 ? createModels.map((m) => ({ name: m.name, verified_at: m.verified_at, verified_ok: m.verified_ok })) : undefined,
      rpm_limit: rpmEl?.value ? parseInt(rpmEl.value, 10) : undefined,
      tpm_limit: tpmEl?.value ? parseInt(tpmEl.value, 10) : undefined,
    }
  }

  async function ensureCreated(): Promise<number | null> {
    if (silentCreatedId) return silentCreatedId
    if (!activePreset) {
      toast.error(t('llm.selectTypeRequired'))
      return null
    }
    const body = getCreateFormBody()
    if (!body.name) {
      toast.error(t('llm.nameRequired'))
      return null
    }
    try {
      const result = await api.post<{ id: number }>('/llm-providers', body)
      const newId = result.id
      setSilentCreatedId(newId)
      queryClient.invalidateQueries({ queryKey: ['llm-providers'] })
      return newId
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : String(err))
      return null
    }
  }

  async function handleCreateVerify(modelName: string) {
    setCreateVerifyingModel(modelName)
    try {
      const id = await ensureCreated()
      if (!id) return

      const body = getCreateFormBody()
      await api.put(`/llm-providers/${id}`, body)

      const result = await api.post<{ success: boolean; message: string }>(
        `/llm-providers/${id}/verify`,
        { model_name: modelName }
      )
      const now = new Date().toISOString()
      const ok = result.success

      if (result.success) {
        toast.success(result.message, { icon: <CheckCircle2 className="h-4 w-4 text-green-500" /> })
      } else {
        toast.error(result.message, { icon: <XCircle className="h-4 w-4 text-red-500" /> })
      }

      setCreateModels((prev) =>
        prev.map((m) => m.name === modelName ? { ...m, verified_at: now, verified_ok: ok } : m)
      )
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : String(err))
    } finally {
      setCreateVerifyingModel(null)
    }
  }

  async function handleCreateFetchModels() {
    setCreateFetchingModels(true)
    try {
      const id = await ensureCreated()
      if (!id) return

      const body = getCreateFormBody()
      await api.put(`/llm-providers/${id}`, body)

      const result = await api.post<{ success: boolean; models: string[]; message: string }>(
        `/llm-providers/${id}/fetch-models`
      )
      if (result.success && result.models.length > 0) {
        setCreateRemoteModels(result.models)
        setCreateRemoteSelected(new Set())
        setCreateRemoteVerified({})
        setCreateRemoteVerifying(null)
        setShowCreateRemotePicker(true)
      } else if (result.success) {
        toast.info(t('llm.noModelsFound'))
      } else {
        toast.error(result.message)
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : String(err))
    } finally {
      setCreateFetchingModels(false)
    }
  }

  function confirmCreateRemoteModels() {
    const existing = new Set(createModels.map((m) => m.name))
    const newModels = [...createRemoteSelected]
      .filter((name) => !existing.has(name))
      .map((name) => {
        const v = createRemoteVerified[name]
        return { name, verified_at: v?.at ?? null, verified_ok: v?.ok ?? null }
      })
    if (newModels.length > 0) {
      setCreateModels((prev) => [...prev, ...newModels])
      toast.success(t('llm.modelsAdded', { count: newModels.length }))
    }
    setShowCreateRemotePicker(false)
  }

  async function handleCreateRemoteVerify(modelName: string) {
    if (!silentCreatedId) return
    setCreateRemoteVerifying(modelName)
    try {
      const result = await api.post<{ success: boolean; message: string }>(
        `/llm-providers/${silentCreatedId}/verify`,
        { model_name: modelName }
      )
      const now = new Date().toISOString()
      setCreateRemoteVerified((prev) => ({ ...prev, [modelName]: { ok: result.success, at: now } }))
      if (result.success) {
        toast.success(result.message, { icon: <CheckCircle2 className="h-4 w-4 text-green-500" /> })
      } else {
        toast.error(result.message, { icon: <XCircle className="h-4 w-4 text-red-500" /> })
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : String(err))
    } finally {
      setCreateRemoteVerifying(null)
    }
  }

  async function cleanupSilentCreated() {
    if (silentCreatedId) {
      try {
        await api.delete(`/llm-providers/${silentCreatedId}`)
        queryClient.invalidateQueries({ queryKey: ['llm-providers'] })
      } catch { /* best effort */ }
    }
  }

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Record<string, unknown> }) =>
      api.put(`/llm-providers/${id}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llm-providers'] })
      setEditTarget(null)
      toast.success(t('llm.updated'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/llm-providers/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llm-providers'] })
      toast.success(t('llm.deleted'))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  async function handleVerify(providerId: number, modelName: string) {
    setVerifyingModel(modelName)
    try {
      const result = await api.post<{ success: boolean; message: string }>(
        `/llm-providers/${providerId}/verify`,
        { model_name: modelName }
      )
      const now = new Date().toISOString()
      const ok = result.success

      if (result.success) {
        toast.success(result.message, { icon: <CheckCircle2 className="h-4 w-4 text-green-500" /> })
      } else {
        toast.error(result.message, { icon: <XCircle className="h-4 w-4 text-red-500" /> })
      }

      setEditModels((prev) =>
        prev.map((m) => m.name === modelName ? { ...m, verified_at: now, verified_ok: ok } : m)
      )
      queryClient.invalidateQueries({ queryKey: ['llm-providers'] })
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : String(err))
    } finally {
      setVerifyingModel(null)
    }
  }

  async function handleEditVerify(modelName: string) {
    if (!editTarget) return
    const body: Record<string, unknown> = { name: editName }
    if (editApiBase) body.api_base = editApiBase
    if (editApiKey) body.api_key = editApiKey
    body.models = editModels.length > 0
      ? editModels.map((m) => ({ name: m.name, verified_at: m.verified_at, verified_ok: m.verified_ok }))
      : null
    body.rpm_limit = editRpm ? parseInt(editRpm, 10) : null
    body.tpm_limit = editTpm ? parseInt(editTpm, 10) : null

    try {
      await api.put(`/llm-providers/${editTarget.id}`, body)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : String(err))
      return
    }

    await handleVerify(editTarget.id, modelName)
  }

  async function handleFetchModels() {
    if (!editTarget) return
    setFetchingModels(true)

    const body: Record<string, unknown> = { name: editName }
    if (editApiBase) body.api_base = editApiBase
    if (editApiKey) body.api_key = editApiKey
    body.models = editModels.length > 0
      ? editModels.map((m) => ({ name: m.name, verified_at: m.verified_at, verified_ok: m.verified_ok }))
      : null
    body.rpm_limit = editRpm ? parseInt(editRpm, 10) : null
    body.tpm_limit = editTpm ? parseInt(editTpm, 10) : null

    try {
      await api.put(`/llm-providers/${editTarget.id}`, body)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : String(err))
      setFetchingModels(false)
      return
    }

    try {
      const result = await api.post<{ success: boolean; models: string[]; message: string }>(
        `/llm-providers/${editTarget.id}/fetch-models`
      )
      if (result.success && result.models.length > 0) {
        setRemoteModels(result.models)
        setRemoteSelected(new Set())
        setRemoteVerified({})
        setRemoteVerifying(null)
        setShowRemotePicker(true)
      } else if (result.success) {
        toast.info(t('llm.noModelsFound'))
      } else {
        toast.error(result.message)
      }
      queryClient.invalidateQueries({ queryKey: ['llm-providers'] })
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : String(err))
    } finally {
      setFetchingModels(false)
    }
  }

  function confirmRemoteModels() {
    const existing = new Set(editModels.map((m) => m.name))
    const newModels = [...remoteSelected]
      .filter((name) => !existing.has(name))
      .map((name) => {
        const v = remoteVerified[name]
        return { name, verified_at: v?.at ?? null, verified_ok: v?.ok ?? null }
      })
    if (newModels.length > 0) {
      setEditModels((prev) => [...prev, ...newModels])
      toast.success(t('llm.modelsAdded', { count: newModels.length }))
    }
    setShowRemotePicker(false)
  }

  async function handleRemoteVerify(modelName: string) {
    if (!editTarget) return
    setRemoteVerifying(modelName)
    try {
      const result = await api.post<{ success: boolean; message: string }>(
        `/llm-providers/${editTarget.id}/verify`,
        { model_name: modelName }
      )
      const now = new Date().toISOString()
      setRemoteVerified((prev) => ({ ...prev, [modelName]: { ok: result.success, at: now } }))
      if (result.success) {
        toast.success(result.message, { icon: <CheckCircle2 className="h-4 w-4 text-green-500" /> })
      } else {
        toast.error(result.message, { icon: <XCircle className="h-4 w-4 text-red-500" /> })
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : String(err))
    } finally {
      setRemoteVerifying(null)
    }
  }

  const [createSubmitting, setCreateSubmitting] = useState(false)

  async function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!activePreset) {
      toast.error(t('llm.selectTypeRequired'))
      return
    }
    const body = getCreateFormBody()

    if (silentCreatedId) {
      setCreateSubmitting(true)
      try {
        await api.put(`/llm-providers/${silentCreatedId}`, body)
        queryClient.invalidateQueries({ queryKey: ['llm-providers'] })
        setSilentCreatedId(null)
        setOpen(false)
        resetCreateForm()
        toast.success(t('llm.added'))
      } catch (err: unknown) {
        toast.error(err instanceof Error ? err.message : String(err))
      } finally {
        setCreateSubmitting(false)
      }
    } else {
      createMutation.mutate(body)
    }
  }

  const dialogOpenChange = async (v: boolean) => {
    if (!v) {
      await cleanupSilentCreated()
      resetCreateForm()
    }
    setOpen(v)
  }

  return (
    <div className={cn("flex flex-col flex-1", !embedded && "overflow-hidden")}>
      <div className={cn("overflow-auto flex-1", embedded ? "p-4" : "p-6")}>
      {!embedded && (
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">{t('llm.title')}</h1>
          <Button onClick={() => setOpen(true)}>{t('llm.addProvider')}</Button>
        </div>
      )}

      <Dialog open={open} onOpenChange={dialogOpenChange}>
          <DialogContent className="max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{t('llm.addTitle')}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label>{t('llm.providerType')}</Label>
                <Select value={selectedPreset} onValueChange={setSelectedPreset}>
                  <SelectTrigger>
                    <SelectValue placeholder={t('llm.selectType')} />
                  </SelectTrigger>
                  <SelectContent>
                    {presetOptions.map((opt) => (
                      <SelectItem key={opt.key} value={opt.key}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="name">{t('llm.providerName')}</Label>
                <Input ref={nameRef} id="name" name="name" required placeholder={t('llm.namePlaceholder')} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="api_base">{t('llm.apiBase')}</Label>
                <Input
                  id="api_base"
                  value={apiBase}
                  onChange={(e) => setApiBase(e.target.value)}
                  placeholder={t('llm.apiBasePlaceholder')}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="create_api_key">{t('llm.apiKey')}</Label>
                <Input id="create_api_key" type="password" placeholder="sk-..." />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>{t('llm.modelList')}</Label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs gap-1"
                    onClick={() => handleCreateFetchModels()}
                    disabled={createFetchingModels}
                  >
                    {createFetchingModels ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Download className="h-3 w-3" />
                    )}
                    {t('llm.fetchModels')}
                  </Button>
                </div>
                <ModelListEditor
                  models={createModels}
                  onChange={setCreateModels}
                  placeholder={t('llm.addModelPlaceholder')}
                  onVerify={(name) => handleCreateVerify(name)}
                  verifyingModel={createVerifyingModel}
                />
              </div>

              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs">{t('llm.rateLimits')}</Label>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="create_rpm_limit" className="text-xs">{t('llm.rpmLimit')}</Label>
                    <Input id="create_rpm_limit" type="number" min="1" placeholder={t('llm.rpmPlaceholder')} />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="create_tpm_limit" className="text-xs">{t('llm.tpmLimit')}</Label>
                    <Input id="create_tpm_limit" type="number" min="1" placeholder={t('llm.tpmPlaceholder')} />
                  </div>
                </div>
              </div>

              <Button type="submit" className="w-full" disabled={createMutation.isPending || createSubmitting}>
                {(createMutation.isPending || createSubmitting) ? t('llm.adding') : t('llm.add')}
              </Button>
            </form>
          </DialogContent>
        </Dialog>

      {isLoading ? (
        <CardLoadingState />
      ) : isError ? (
        <div className="text-center py-12 text-destructive">{t('error.loadFailed')}</div>
      ) : !data?.items?.length ? (
        <EmptyState title={t('llm.emptyHint')} />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {data.items.map((provider) => (
            <Card
              key={provider.id}
              className="cursor-pointer hover:bg-accent/50 transition-colors"
              onClick={() => {
                setEditTarget(provider)
                setEditName(provider.name)
                setEditApiBase(provider.api_base || '')
                setEditApiKey('')
                setEditRpm(provider.rpm_limit != null ? String(provider.rpm_limit) : '')
                setEditTpm(provider.tpm_limit != null ? String(provider.tpm_limit) : '')
                setEditModels(provider.models ?? [])
              }}
            >
              <CardHeader className="pb-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap min-w-0">
                    <CardTitle className="text-base truncate">{provider.name}</CardTitle>
                    <Badge variant="outline">{provider.provider_type}</Badge>
                    <Badge variant={provider.is_active ? 'default' : 'secondary'}>
                      {provider.is_active ? t('llm.active') : t('llm.inactive')}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
                  {provider.api_base && <span>API: {provider.api_base}</span>}
                  {provider.api_key_masked && (
                    <span>Key: {provider.api_key_masked}</span>
                  )}
                  {provider.rpm_limit != null && (
                    <span>RPM: {provider.rpm_limit}</span>
                  )}
                  {provider.tpm_limit != null && (
                    <span>TPM: {provider.tpm_limit.toLocaleString()}</span>
                  )}
                </div>
                {provider.models && provider.models.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {provider.models.map((m) => (
                      <Badge
                        key={m.name}
                        variant="secondary"
                        className="text-xs gap-1"
                      >
                        {m.verified_ok === true && <CheckCircle2 className="h-3 w-3 text-green-500" />}
                        {m.verified_ok === false && <XCircle className="h-3 w-3 text-red-500" />}
                        {m.name}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={!!editTarget} onOpenChange={(v) => { if (!v) setEditTarget(null) }}>
        <DialogContent className="max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('llm.editTitle')}</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              if (!editTarget) return
              const body: Record<string, unknown> = { name: editName }
              if (editApiBase) body.api_base = editApiBase
              if (editApiKey) body.api_key = editApiKey
              body.models = editModels.length > 0 ? editModels.map((m) => ({ name: m.name, verified_at: m.verified_at, verified_ok: m.verified_ok })) : null
              body.rpm_limit = editRpm ? parseInt(editRpm, 10) : null
              body.tpm_limit = editTpm ? parseInt(editTpm, 10) : null
              updateMutation.mutate({ id: editTarget.id, body })
            }}
            className="space-y-4"
          >
            <div className="space-y-2">
              <Label>{t('llm.providerName')}</Label>
              <Input value={editName} onChange={(e) => setEditName(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label>{t('llm.apiBase')}</Label>
              <Input
                value={editApiBase}
                onChange={(e) => setEditApiBase(e.target.value)}
                placeholder={t('llm.apiBasePlaceholder')}
              />
            </div>
            <div className="space-y-2">
              <Label>{t('llm.apiKey')}</Label>
              <Input
                type="password"
                value={editApiKey}
                onChange={(e) => setEditApiKey(e.target.value)}
                placeholder={editTarget?.api_key_masked || 'sk-...'}
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>{t('llm.modelList')}</Label>
                {editTarget && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs gap-1"
                    onClick={() => handleFetchModels()}
                    disabled={fetchingModels}
                  >
                    {fetchingModels ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Download className="h-3 w-3" />
                    )}
                    {t('llm.fetchModels')}
                  </Button>
                )}
              </div>
              <ModelListEditor
                models={editModels}
                onChange={setEditModels}
                placeholder={t('llm.addModelPlaceholder')}
                onVerify={editTarget ? (name) => handleEditVerify(name) : undefined}
                verifyingModel={verifyingModel}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-muted-foreground text-xs">{t('llm.rateLimits')}</Label>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs">{t('llm.rpmLimit')}</Label>
                  <Input
                    type="number"
                    min="1"
                    value={editRpm}
                    onChange={(e) => setEditRpm(e.target.value)}
                    placeholder={t('llm.rpmPlaceholder')}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t('llm.tpmLimit')}</Label>
                  <Input
                    type="number"
                    min="1"
                    value={editTpm}
                    onChange={(e) => setEditTpm(e.target.value)}
                    placeholder={t('llm.tpmPlaceholder')}
                  />
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <Button type="submit" className="flex-1" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? t('common.saving') : t('common.save')}
              </Button>
              <Button
                type="button"
                variant="destructive"
                onClick={() => setDeleteTarget(editTarget)}
              >
                {t('common.delete')}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <DeleteConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => { if (!o) setDeleteTarget(null) }}
        itemName={deleteTarget?.name ?? ''}
        descriptionKey="llm.confirmDelete"
        onConfirm={() => {
          if (deleteTarget) { deleteMutation.mutate(deleteTarget.id); setEditTarget(null) }
          setDeleteTarget(null)
        }}
      />

      <Dialog open={showRemotePicker} onOpenChange={setShowRemotePicker}>
        <DialogContent className="max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>{t('llm.selectModelsTitle')}</DialogTitle>
          </DialogHeader>
          <div className="flex items-center gap-2 mb-2">
            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={() => {
                const existing = new Set(editModels.map((m) => m.name))
                const allNew = remoteModels.filter((n) => !existing.has(n))
                setRemoteSelected(new Set(allNew))
              }}
            >
              {t('llm.selectAll')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={() => setRemoteSelected(new Set())}
            >
              {t('llm.deselectAll')}
            </Button>
            <span className="text-xs text-muted-foreground ml-auto">
              {remoteSelected.size} / {remoteModels.length}
            </span>
          </div>
          <div className="flex-1 overflow-y-auto rounded-md border divide-y">
            {remoteModels.map((name) => {
              const alreadyAdded = editModels.some((m) => m.name === name)
              const checked = remoteSelected.has(name)
              const vStatus = remoteVerified[name]
              return (
                <div
                  key={name}
                  className={`flex items-center gap-3 px-3 py-2 hover:bg-accent/50 ${alreadyAdded ? 'opacity-50' : ''}`}
                >
                  <input
                    type="checkbox"
                    className="rounded border-input h-4 w-4 shrink-0 cursor-pointer"
                    checked={checked || alreadyAdded}
                    disabled={alreadyAdded}
                    onChange={() => {
                      if (alreadyAdded) return
                      const next = new Set(remoteSelected)
                      if (checked) next.delete(name)
                      else next.add(name)
                      setRemoteSelected(next)
                    }}
                  />
                  {vStatus?.ok === true && <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />}
                  {vStatus?.ok === false && <XCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />}
                  {!vStatus && !alreadyAdded && <div className="h-3.5 w-3.5 rounded-full border-2 border-muted-foreground/30 shrink-0" />}
                  <span className="text-sm flex-1 min-w-0 truncate">{name}</span>
                  {alreadyAdded ? (
                    <Badge variant="secondary" className="text-xs shrink-0">{t('llm.alreadyAdded')}</Badge>
                  ) : (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-xs shrink-0"
                      onClick={() => handleRemoteVerify(name)}
                      disabled={remoteVerifying === name}
                    >
                      {remoteVerifying === name ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <CheckCircle2 className="h-3 w-3" />
                      )}
                    </Button>
                  )}
                </div>
              )
            })}
          </div>
          <Button
            className="w-full mt-3"
            disabled={remoteSelected.size === 0}
            onClick={confirmRemoteModels}
          >
            {t('llm.addSelected', { count: remoteSelected.size })}
          </Button>
        </DialogContent>
      </Dialog>

      <Dialog open={showCreateRemotePicker} onOpenChange={setShowCreateRemotePicker}>
        <DialogContent className="max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>{t('llm.selectModelsTitle')}</DialogTitle>
          </DialogHeader>
          <div className="flex items-center gap-2 mb-2">
            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={() => {
                const existing = new Set(createModels.map((m) => m.name))
                const allNew = createRemoteModels.filter((n) => !existing.has(n))
                setCreateRemoteSelected(new Set(allNew))
              }}
            >
              {t('llm.selectAll')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={() => setCreateRemoteSelected(new Set())}
            >
              {t('llm.deselectAll')}
            </Button>
            <span className="text-xs text-muted-foreground ml-auto">
              {createRemoteSelected.size} / {createRemoteModels.length}
            </span>
          </div>
          <div className="flex-1 overflow-y-auto rounded-md border divide-y">
            {createRemoteModels.map((name) => {
              const alreadyAdded = createModels.some((m) => m.name === name)
              const checked = createRemoteSelected.has(name)
              const vStatus = createRemoteVerified[name]
              return (
                <div
                  key={name}
                  className={`flex items-center gap-3 px-3 py-2 hover:bg-accent/50 ${alreadyAdded ? 'opacity-50' : ''}`}
                >
                  <input
                    type="checkbox"
                    className="rounded border-input h-4 w-4 shrink-0 cursor-pointer"
                    checked={checked || alreadyAdded}
                    disabled={alreadyAdded}
                    onChange={() => {
                      if (alreadyAdded) return
                      const next = new Set(createRemoteSelected)
                      if (checked) next.delete(name)
                      else next.add(name)
                      setCreateRemoteSelected(next)
                    }}
                  />
                  {vStatus?.ok === true && <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />}
                  {vStatus?.ok === false && <XCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />}
                  {!vStatus && !alreadyAdded && <div className="h-3.5 w-3.5 rounded-full border-2 border-muted-foreground/30 shrink-0" />}
                  <span className="text-sm flex-1 min-w-0 truncate">{name}</span>
                  {alreadyAdded ? (
                    <Badge variant="secondary" className="text-xs shrink-0">{t('llm.alreadyAdded')}</Badge>
                  ) : (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-xs shrink-0"
                      onClick={() => handleCreateRemoteVerify(name)}
                      disabled={createRemoteVerifying === name}
                    >
                      {createRemoteVerifying === name ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <CheckCircle2 className="h-3 w-3" />
                      )}
                    </Button>
                  )}
                </div>
              )
            })}
          </div>
          <Button
            className="w-full mt-3"
            disabled={createRemoteSelected.size === 0}
            onClick={confirmCreateRemoteModels}
          >
            {t('llm.addSelected', { count: createRemoteSelected.size })}
          </Button>
        </DialogContent>
      </Dialog>
    </div>
    </div>
  )
}
