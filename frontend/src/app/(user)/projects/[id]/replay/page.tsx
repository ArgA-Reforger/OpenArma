'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'
import type { LandmarkData, ZoneData, RoadData } from '@/types/map'
import {
  ReplayViewer,
  type ReplayMetadata,
  type FrameData,
  type ReplayMapData,
  type ReplayTileInfo,
} from '@/components/replay/replay-viewer'

export default function ReplayPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const projectId = params.id as string
  const groupId = searchParams.get('group')
  const api = useApi()
  const { t } = useI18n()

  const [frames, setFrames] = useState<FrameData[]>([])
  const [activeSessionIdx, setActiveSessionIdx] = useState(0)

  const { data: project } = useQuery<{ id: string; name: string; map_id: number | null }>({
    queryKey: ['project', projectId],
    queryFn: () => api.get(`/projects/${projectId}`),
    enabled: !!projectId,
  })

  const mapId = project?.map_id

  const { data: mapData } = useQuery<ReplayMapData>({
    queryKey: ['map-detail', mapId],
    queryFn: () => api.get(`/maps/admin/maps/${mapId}`),
    enabled: !!mapId,
  })

  const { data: tileInfo } = useQuery<ReplayTileInfo>({
    queryKey: ['tile-info', mapId],
    queryFn: () => api.get(`/maps/admin/maps/${mapId}/tiles/info`),
    enabled: !!mapId,
  })

  const { data: landmarks } = useQuery<LandmarkData[]>({
    queryKey: ['map-landmarks-admin', mapId],
    queryFn: () => api.get(`/maps/admin/maps/${mapId}/landmarks?limit=2000`),
    enabled: !!mapId,
  })
  const { data: zones } = useQuery<ZoneData[]>({
    queryKey: ['map-zones-admin', mapId],
    queryFn: () => api.get(`/maps/admin/maps/${mapId}/zones`),
    enabled: !!mapId,
  })
  const { data: roads } = useQuery<RoadData[]>({
    queryKey: ['map-roads-admin', mapId],
    queryFn: () => api.get(`/maps/admin/maps/${mapId}/roads`),
    enabled: !!mapId,
  })

  const groupQuery = groupId ? `?group_id=${groupId}` : ''

  const { data: metadata } = useQuery<ReplayMetadata>({
    queryKey: ['replay-metadata', projectId, groupId],
    queryFn: () => api.get(`/open/admin/replay/${projectId}/metadata${groupQuery}`),
    enabled: !!projectId,
  })

  const session = metadata?.sessions[activeSessionIdx]

  useEffect(() => {
    if (!session || !projectId) return
    const gp = groupId ? `&group_id=${groupId}` : ''
    api.get<{ frames: FrameData[] }>(
      `/open/admin/replay/${projectId}/frames?from=${session.start_frame}&to=${session.end_frame}${gp}`
    ).then((res) => {
      setFrames(res.frames)
    })
  }, [session, projectId]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!metadata || !mapData || frames.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
          <p className="text-sm text-muted-foreground">
            {!metadata ? t('replay.loadingMetadata') : !mapData ? t('replay.noMap') : t('replay.loadingFrames')}
          </p>
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-1" /> {t('replay.back')}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <ReplayViewer
      title={project?.name || ''}
      metadata={metadata}
      mapData={mapData}
      tileInfo={tileInfo}
      frames={frames}
      landmarks={landmarks}
      zones={zones}
      roads={roads}
      onBack={() => router.back()}
      onSessionChange={setActiveSessionIdx}
    />
  )
}
