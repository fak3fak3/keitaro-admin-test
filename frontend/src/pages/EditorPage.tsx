import { useUnit } from 'effector-react'
import { useEffect } from 'react'
import { Link, useParams } from 'react-router'

import { StreamCard } from '@/components/editor/StreamCard'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  $editorError,
  $streams,
  editorOpened,
  errorDismissed,
  fetchClicked,
  fetchMutation,
  streamsQuery,
} from '@/models/editor'

export function EditorPage() {
  const campaignId = Number(useParams().campaignId)
  const [streams, loaded, fetching, error] = useUnit([
    $streams,
    streamsQuery.$finished,
    fetchMutation.$pending,
    $editorError,
  ])
  const [opened, fetch, dismiss] = useUnit([editorOpened, fetchClicked, errorDismissed])

  useEffect(() => {
    opened(campaignId)
  }, [opened, campaignId])

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav aria-label="Хлебные крошки" className="text-sm text-muted-foreground">
          <Link to="/" className="hover:underline">Кампании</Link>
          {' / '}Кампания {campaignId}{' / '}
          <span className="text-foreground">Keitaro Streams</span>
        </nav>
        <Button onClick={() => fetch()} disabled={fetching}>
          {fetching ? 'Загружаем…' : 'Fetch streams from KT'}
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="flex items-start justify-between gap-3">
          <AlertDescription>{error}</AlertDescription>
          <Button variant="ghost" size="sm" onClick={() => dismiss()}>Закрыть</Button>
        </Alert>
      )}

      {loaded && streams.length === 0 && (
        <p className="text-muted-foreground">
          Потоки кампании ещё не загружены. Нажмите Fetch streams from KT.
        </p>
      )}

      {streams.map((stream) => (
        <StreamCard key={stream.id} stream={stream} />
      ))}
    </section>
  )
}
