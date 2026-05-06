'use client'

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import zhCN from './locales/zh-CN.json'
import enUS from './locales/en-US.json'

export type Locale = 'zh-CN' | 'en-US'

const locales: Record<Locale, Record<string, unknown>> = {
  'zh-CN': zhCN as Record<string, unknown>,
  'en-US': enUS as Record<string, unknown>,
}

interface I18nContextValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (key: string, params?: Record<string, string | number>) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

function getNestedValue(obj: Record<string, unknown>, key: string): string {
  const parts = key.split('.')
  let current: unknown = obj
  for (const part of parts) {
    if (current == null || typeof current !== 'object') return key
    current = (current as Record<string, unknown>)[part]
  }
  return typeof current === 'string' ? current : key
}

function interpolate(template: string, params?: Record<string, string | number>): string {
  if (!params) return template
  return template.replace(/\{(\w+)\}/g, (_, k) => String(params[k] ?? `{${k}}`))
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('locale') as Locale | null
      if (saved && saved in locales) return saved
    }
    return 'zh-CN'
  })

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale)
    if (typeof window !== 'undefined') {
      localStorage.setItem('locale', newLocale)
      document.documentElement.lang = newLocale
    }
  }, [])

  const t = useCallback(
    (key: string, params?: Record<string, string | number>) => {
      const value = getNestedValue(locales[locale], key)
      return interpolate(value, params)
    },
    [locale],
  )

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within I18nProvider')
  return ctx
}
