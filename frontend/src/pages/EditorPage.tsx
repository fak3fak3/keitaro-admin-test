import { useUnit } from 'effector-react'
import { Loader2, RefreshCw } from 'lucide-react'
import { useEffect } from 'react'
import { Link, useParams } from 'react-router'

import { LiveIndicator } from '@/components/editor/LiveIndicator'
import { Notice } from '@/components/editor/Notice'
import { StreamCard } from '@/components/editor/StreamCard'
import { Button } from '@/components/ui/button'
import {
  $campaignName,
  $editorError,
  $liveError,
  $streams,
  editorClosed,
  editorOpened,
  errorDismissed,
  fetchClicked,
  fetchMutation,
  streamsQuery,
} from '@/models/editor'

export function EditorPage() {
  const campaignId = Number(useParams().campaignId)
  const [streams, status, fetching, error, liveError, campaignName] = useUnit([
    $streams,
    streamsQuery.$status,
    fetchMutation.$pending,
    $editorError,
    $liveError,
    $campaignName,
  ])
  const [opened, closed, fetch, dismiss] = useUnit([
    editorOpened,
    editorClosed,
    fetchClicked,
    errorDismissed,
  ])

  // Пока страница открыта — live-соединение (бэкенд опрашивает Keitaro); ушли — закрываем
  useEffect(() => {
    opened(campaignId)
    return () => {
      closed()
    }
  }, [opened, closed, campaignId])

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav aria-label="Хлебные крошки" className="text-sm text-muted-foreground">
          <Link to="/" className="hover:underline">Кампании</Link>
          {' / '}
          <span className="text-foreground">{campaignName ?? `Кампания ${campaignId}`}</span>
          {' / '}Keitaro Streams
        </nav>
        <div className="flex items-center gap-4">
          <LiveIndicator />
          <Button onClick={() => fetch()} disabled={fetching}>
            {fetching ? <Loader2 aria-hidden className="animate-spin" /> : <RefreshCw aria-hidden />}
            {fetching ? 'Загружаем…' : 'Fetch streams from KT'}
          </Button>
        </div>
      </div>

      {/* Уровень кампании: загрузка, Fetch и опрос Keitaro. Ошибки действий — на своих потоках. */}
      {error && (
        <Notice
          tone="error"
          role="alert"
          actions={<Button variant="ghost" size="xs" onClick={() => dismiss()}>Закрыть</Button>}
        >
          {error}
        </Notice>
      )}

      {liveError && (
        <Notice tone="warning" role="status">
          <p className="font-medium">Keitaro не отвечает — изменения из трекера не приходят.</p>
          <p className="text-xs opacity-80">{liveError}</p>
        </Notice>
      )}

      {status === 'pending' && streams.length === 0 && (
        <p className="flex items-center gap-2 py-8 text-muted-foreground">
          <Loader2 aria-hidden className="size-4 animate-spin" />
          Загружаем потоки…
        </p>
      )}

      {status === 'done' && streams.length === 0 && (
        <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">
          Потоки кампании ещё не загружены. Нажмите Fetch streams from KT — они придут из Keitaro.
        </div>
      )}

      {streams.map((stream) => (
        <StreamCard key={stream.id} stream={stream} />
      ))}
    </section>
  )
}
