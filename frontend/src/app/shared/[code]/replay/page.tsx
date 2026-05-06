'use client'

import { use, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useI18n } from '@/lib/i18n'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import type { LandmarkData, ZoneData, RoadData } from '@/types/map'
import {
  ReplayViewer,
  type ReplayMetadata,
  type FrameData,
  type ReplayMapData,
  type ReplayTileInfo,
} from '@/components/replay/replay-viewer'
import { LocaleSwitcher } from '@/components/locale-switcher'

interface ReplayInfo {
  has_replay: boolean
  project_name: string
  map: ReplayMapData | null
  conversation_group_id: number | null
}

export default function SharedReplayPage({
  params,
}: {
  params: Promise<{ code: string }>
}) {
  const { code } = use(params)
  const router = useRouter()
  const { t } = useI18n()

  const [frames, setFrames] = useState<FrameData[]>([])
  const [activeSessionIdx, setActiveSessionIdx] = useState(0)

  const { data: info, isLoading: infoLoading, isError } = useQuery<ReplayInfo>({
    queryKey: ['shared-replay-info', code],
    queryFn: () => api.get(`/shared/${code}/replay/info`),
  })

  const mapId = info?.map?.id

  const { data: tileInfo } = useQuery<ReplayTileInfo>({
    queryKey: ['shared-tile-info', code, mapId],
    queryFn: () => api.get(`/shared/${code}/replay/map/${mapId}/tiles/info`),
    enabled: !!mapId,
  })

  const { data: metadata } = useQuery<ReplayMetadata>({
    queryKey: ['shared-replay-metadata', code],
    queryFn: () => api.get(`/shared/${code}/replay/metadata`),
    enabled: info?.has_replay === true,
  })

  const { data: landmarks } = useQuery<LandmarkData[]>({
    queryKey: ['shared-replay-landmarks', code, mapId],
    queryFn: () => api.get(`/shared/${code}/replay/map/${mapId}/landmarks?limit=2000`),
    enabled: !!mapId,
  })
  const { data: zones } = useQuery<ZoneData[]>({
    queryKey: ['shared-replay-zones', code, mapId],
    queryFn: () => api.get(`/shared/${code}/replay/map/${mapId}/zones`),
    enabled: !!mapId,
  })
  const { data: roads } = useQuery<RoadData[]>({
    queryKey: ['shared-replay-roads', code, mapId],
    queryFn: () => api.get(`/shared/${code}/replay/map/${mapId}/roads`),
    enabled: !!mapId,
  })

  const session = metadata?.sessions[activeSessionIdx]

  useEffect(() => {
    if (!session || !code) return
    api.get<{ frames: FrameData[] }>(
      `/shared/${code}/replay/frames?from=${session.start_frame}&to=${session.end_frame}`
    ).then((res) => {
      setFrames(res.frames)
    })
  }, [session, code])

  if (infoLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    )
  }

  if (isError || !info) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-bold">{t('shared.invalidLink')}</h1>
          <p className="text-muted-foreground">{t('shared.invalidDesc')}</p>
          <Link href="/login">
            <Button>{t('shared.goLogin')}</Button>
          </Link>
        </div>
      </div>
    )
  }

  if (!info.has_replay) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-xl font-semibold">{t('replay.noData') || 'No replay data'}</h1>
          <p className="text-muted-foreground">{info.project_name}</p>
          <Button variant="ghost" size="sm" onClick={() => router.push(`/shared/${code}`)}>
            <ArrowLeft className="h-4 w-4 mr-1" /> {t('replay.back')}
          </Button>
        </div>
      </div>
    )
  }

  if (!metadata || !info.map || frames.length === 0) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
          <p className="text-sm text-muted-foreground">
            {!metadata ? t('replay.loadingMetadata') : !info.map ? t('replay.noMap') : t('replay.loadingFrames')}
          </p>
          <Button variant="ghost" size="sm" onClick={() => router.push(`/shared/${code}`)}>
            <ArrowLeft className="h-4 w-4 mr-1" /> {t('replay.back')}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <header className="border-b px-4 py-2 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => router.push(`/shared/${code}`)}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-sm font-semibold">{info.project_name} — {t('replay.title')}</h1>
            <p className="text-xs text-muted-foreground">{t('shared.sharedVia')}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <LocaleSwitcher />
          <Link href="/login">
            <Button variant="outline" size="sm">{t('shared.loginToUse')}</Button>
          </Link>
        </div>
      </header>

      <div className="flex-1 min-h-0">
        <ReplayViewer
          title={info.project_name}
          metadata={metadata}
          mapData={info.map}
          tileInfo={tileInfo}
          frames={frames}
          landmarks={landmarks}
          zones={zones}
          roads={roads}
          onSessionChange={setActiveSessionIdx}
        />
      </div>
    </div>
  )
}
