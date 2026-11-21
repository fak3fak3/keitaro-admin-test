import { useUnit } from 'effector-react'
import { Loader2 } from 'lucide-react'

import type { Stream, StreamOffer } from '@/api/streams'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { plural } from '@/lib/plural'
import { cn } from '@/lib/utils'
import { $busyStreams, actionRequested } from '@/models/editor'
import { streamSummary } from '@/models/streamSummary'

import { AddOffer } from './AddOffer'
import { ConflictChoice, KeitaroMark } from './KeitaroMarks'
import { ShareCell } from './ShareCell'
import { StreamNotices } from './StreamNotices'

export function StreamCard({ stream }: { stream: Stream }) {
  const [busyStreams, act] = useUnit([$busyStreams, actionRequested])
  const busy = busyStreams.includes(stream.id)
  const streamId = stream.id
  const summary = streamSummary(stream)
  const hasOffers = stream.offers.length > 0

  return (
    // Черновик — жёлтый поток, как в видео: есть изменения, которых ещё нет в Keitaro
    <article
      aria-label={stream.name}
      aria-busy={busy}
      className={cn(
        'space-y-3 rounded-xl border bg-card p-4 transition-colors',
        stream.has_draft && 'border-amber-300 border-l-4 border-l-amber-400 bg-amber-50/60 dark:border-amber-800 dark:bg-amber-950/20',
      )}
    >
      <header className="flex flex-wrap items-center gap-2">
        <h2 className="font-semibold">
          {stream.name}
          <span className="ml-2 text-sm font-normal text-muted-foreground">
            #{stream.position} · stream {stream.id}
          </span>
        </h2>
        {stream.has_draft && (
          <Badge className="bg-amber-400 text-amber-950">
            Черновик · {summary.changes} {plural(summary.changes, ['изменение', 'изменения', 'изменений'])}
          </Badge>
        )}
        {busy && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Loader2 aria-hidden className="size-3.5 animate-spin" />
            Сохраняем…
          </span>
        )}
      </header>

      <StreamNotices stream={stream} summary={summary} disabled={busy} />

      {!hasOffers && (
        <p className="text-sm text-muted-foreground">
          Офферов нет — фильтры и редирект этого потока настраиваются в Keitaro.
        </p>
      )}

      {hasOffers && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Оффер</TableHead>
              <TableHead className="w-44">Share</TableHead>
              <TableHead className="w-32 text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {stream.offers.map((offer) => (
              <OfferRow key={offer.offer_id} streamId={stream.id} offer={offer} disabled={busy} />
            ))}
          </TableBody>
          <TableFooter className="bg-transparent">
            <TableRow>
              <TableCell className="text-muted-foreground">Итого</TableCell>
              <TableCell className={cn('px-4 font-semibold', summary.warnings.length > 0 && 'text-amber-700 dark:text-amber-400')}>
                {summary.total}%
              </TableCell>
              <TableCell />
            </TableRow>
          </TableFooter>
        </Table>
      )}

      {hasOffers && (
        <footer className="flex flex-wrap items-center justify-end gap-2">
          <div className="mr-auto flex flex-1">
            <AddOffer streamId={streamId} disabled={busy} />
          </div>
          <Button variant="outline" disabled={busy || !stream.has_draft} onClick={() => act({ kind: 'cancel', streamId })}>
            Cancel
          </Button>
          <Button
            disabled={busy || !stream.has_draft || stream.has_conflicts}
            onClick={() => act({ kind: 'push', streamId })}
          >
            Push to KT
          </Button>
        </footer>
      )}
    </article>
  )
}

type OfferRowProps = { streamId: number; offer: StreamOffer; disabled: boolean }

function OfferRow({ streamId, offer, disabled }: OfferRowProps) {
  const act = useUnit(actionRequested)
  const removed = offer.status === 'removed'
  const unpublished = offer.published_status === null
  const before = offer.changed && !unpublished && offer.published_share !== offer.share ? offer.published_share : null
  const target = { streamId, offerId: offer.offer_id }

  return (
    <TableRow className={cn(offer.changed && 'bg-amber-100/50 dark:bg-amber-900/20')}>
      <TableCell className="whitespace-normal">
        <div className="flex flex-wrap items-center gap-2">
          <span className={cn('font-medium', removed && 'text-muted-foreground line-through decoration-muted-foreground/50')}>
            {offer.offer_name}
          </span>
          {removed && <Badge variant="secondary">removed</Badge>}
          {unpublished && !removed && <Badge variant="outline" className="border-amber-400">новый</Badge>}
        </div>
        <div className="text-xs text-muted-foreground">id {offer.offer_id}</div>
        <KeitaroMark offer={offer} />
        <ConflictChoice streamId={streamId} offer={offer} disabled={disabled} />
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <ShareCell streamId={streamId} offer={offer} disabled={disabled} />
          {before !== null && <span className="text-xs text-muted-foreground">было {before}%</span>}
        </div>
      </TableCell>
      <TableCell className="text-right">
        {removed ? (
          <Button variant="outline" size="sm" disabled={disabled} onClick={() => act({ kind: 'bringBack', ...target })}>
            Bring back
          </Button>
        ) : (
          <Button variant="outline" size="sm" disabled={disabled} onClick={() => act({ kind: 'remove', ...target })}>
            Remove
          </Button>
        )}
      </TableCell>
    </TableRow>
  )
}
