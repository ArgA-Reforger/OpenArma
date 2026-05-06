export interface PageData<T> {
  items: T[]
  total: number
}

export interface EmbeddedProps {
  embedded?: boolean
  addDialogOpen?: boolean
  onAddDialogOpenChange?: (v: boolean) => void
}

export interface ModelEntry {
  name: string
  verified_at: string | null
  verified_ok: boolean | null
}

export interface LLMProviderBase {
  id: number
  name: string
  provider_type: string
  models: ModelEntry[] | null
}

export interface ResourceBase {
  id: number | string
  name: string
  visibility?: string
  user_id?: number
}
