'use client'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Map as MapIcon, ChevronDown, Check } from 'lucide-react'
import { useI18n } from '@/lib/i18n'
import type { GameMap } from '@/types/map'

interface MapSelectorProps {
  maps: GameMap[]
  selectedMapId: number | null
  onSelect: (id: number) => void
  isAdmin: boolean
}

export function MapSelector({ maps, selectedMapId, onSelect, isAdmin }: MapSelectorProps) {
  const { t } = useI18n()
  const visibleMaps = isAdmin ? maps : maps.filter(m => m.status === 'published')
  const selectedMap = visibleMaps.find(m => m.id === selectedMapId)

  if (visibleMaps.length === 0) return null

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="secondary" size="sm" className="h-8 gap-1.5 shadow-md text-xs">
          <MapIcon className="h-3.5 w-3.5" />
          <span className="max-w-[120px] truncate">{selectedMap?.name || t('thematic.selectMap')}</span>
          <ChevronDown className="h-3 w-3 opacity-60" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56 z-[1100]">
        {visibleMaps.map(m => (
          <DropdownMenuItem
            key={m.id}
            onClick={() => onSelect(m.id)}
            className="flex items-center justify-between"
          >
            <div className="min-w-0">
              <div className="text-sm truncate">{m.name}</div>
              <div className="text-[10px] text-muted-foreground">
                {m.size_x}m × {m.size_z}m
                {isAdmin && m.status === 'draft' && ` · ${t('thematic.draft')}`}
              </div>
            </div>
            {m.id === selectedMapId && <Check className="h-3.5 w-3.5 shrink-0 text-primary" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
