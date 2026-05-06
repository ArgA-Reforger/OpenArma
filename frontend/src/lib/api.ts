const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1'

export function getBackendOrigin(): string {
  try {
    return new URL(API_BASE).origin
  } catch {
    return ''
  }
}

function safeParse(text: string): unknown {
  let out = ''
  let i = 0
  const len = text.length
  while (i < len) {
    const ch = text[i]
    if (ch === '"') {
      const start = i
      i++
      while (i < len) {
        if (text[i] === '\\') { i += 2; continue }
        if (text[i] === '"') { i++; break }
        i++
      }
      out += text.slice(start, i)
    } else if (ch === '-' || (ch >= '0' && ch <= '9')) {
      const start = i
      if (ch === '-') i++
      while (i < len && text[i] >= '0' && text[i] <= '9') i++
      const hasDot = i < len && text[i] === '.'
      if (hasDot) { i++; while (i < len && text[i] >= '0' && text[i] <= '9') i++ }
      const hasExp = i < len && (text[i] === 'e' || text[i] === 'E')
      if (hasExp) { i++; if (i < len && (text[i] === '+' || text[i] === '-')) i++; while (i < len && text[i] >= '0' && text[i] <= '9') i++ }
      const numStr = text.slice(start, i)
      if (!hasDot && !hasExp && numStr.length >= 16 && Number(numStr) > Number.MAX_SAFE_INTEGER) {
        out += `"${numStr}"`
      } else {
        out += numStr
      }
    } else {
      out += ch
      i++
    }
  }
  return JSON.parse(out)
}

interface ApiOptions extends RequestInit {
  token?: string
}

class ApiError extends Error {
  constructor(
    public status: number,
    public code: number,
    message: string,
    public data?: unknown,
  ) {
    super(message)
  }
}

let _onUnauthorized: (() => void) | null = null

export function setOnUnauthorized(handler: () => void) {
  _onUnauthorized = handler
}

function handleUnauthorized() {
  if (_onUnauthorized) {
    _onUnauthorized()
  } else if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
    window.location.href = '/login'
  }
}

async function request<T = unknown>(path: string, options: ApiOptions = {}): Promise<T> {
  const { token, headers: customHeaders, ...rest } = options
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(customHeaders as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, { headers, ...rest })
  const text = await res.text()
  const json = safeParse(text) as { code: number; msg: string; data: unknown }

  if (res.status === 401 || json.code === 401) {
    handleUnauthorized()
    throw new ApiError(res.status, json.code || 401, json.msg || 'Unauthorized', json.data)
  }

  if (!res.ok || json.code !== 200) {
    throw new ApiError(res.status, json.code, json.msg, json.data)
  }

  return json.data as T
}

async function uploadRequest<T = unknown>(path: string, formData: FormData, options: ApiOptions = {}): Promise<T> {
  const { token, headers: customHeaders, ...rest } = options
  const headers: Record<string, string> = {
    ...(customHeaders as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, { headers, method: 'POST', body: formData, ...rest })
  const text = await res.text()
  const json = safeParse(text) as { code: number; msg: string; data: unknown }

  if (res.status === 401 || json.code === 401) {
    handleUnauthorized()
    throw new ApiError(res.status, json.code || 401, json.msg || 'Unauthorized', json.data)
  }

  if (!res.ok || json.code !== 200) {
    throw new ApiError(res.status, json.code, json.msg, json.data)
  }

  return json.data as T
}

export const api = {
  get: <T = unknown>(path: string, options?: ApiOptions) =>
    request<T>(path, { ...options, method: 'GET' }),
  post: <T = unknown>(path: string, body?: unknown, options?: ApiOptions) =>
    request<T>(path, { ...options, method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T = unknown>(path: string, body?: unknown, options?: ApiOptions) =>
    request<T>(path, { ...options, method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  delete: <T = unknown>(path: string, body?: unknown, options?: ApiOptions) =>
    request<T>(path, { ...options, method: 'DELETE', body: body ? JSON.stringify(body) : undefined }),
  upload: <T = unknown>(path: string, formData: FormData, options?: ApiOptions) =>
    uploadRequest<T>(path, formData, options),
}

export { ApiError }
