'use client'

import { useI18n, type Locale } from '@/lib/i18n'
import { Button } from '@/components/ui/button'

const LOCALES: { value: Locale; label: string }[] = [
  { value: 'es-ES', label: 'ES' },
  { value: 'en-US', label: 'EN' },
]

export function LocaleSwitcher() {
  const { locale, setLocale } = useI18n()

  return (
    <div className="flex gap-0.5 rounded-lg border bg-background/80 backdrop-blur-sm p-0.5 shadow-sm" role="radiogroup" aria-label="Language">
      {LOCALES.map((l) => (
        <Button
          key={l.value}
          variant={locale === l.value ? 'secondary' : 'ghost'}
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={() => setLocale(l.value)}
          aria-pressed={locale === l.value}
          aria-label={`Switch to ${l.label}`}
        >
          {l.label}
        </Button>
      ))}
    </div>
  )
}
