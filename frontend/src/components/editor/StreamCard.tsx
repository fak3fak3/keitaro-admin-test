import { useUnit } from 'effector-react'

import type { Stream, StreamOffer } from '@/api/streams'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { $busyStreams, actionRequested } from '@/models/editor'
import { cn } from '@/lib/utils'

import { AddOffer } from './AddOffer'
import { ConflictChoice, KeitaroMark } from './KeitaroMarks'
import { ShareCell } from './ShareCell'

export function StreamCard({ stream }: { stream: Stream }) {
  const [busyStreams, act] = useUnit([$busyStreams, actionRequested])
  const busy = busyStreams.includes(stream.id)
  const streamId = stream.id
  const hasMarks = stream.offers.some((offer) => offer.keitaro_change !== null)

  return (
    // Черновик — жёлтый поток, как в видео: есть изменения, которых ещё нет в Keitaro
    <article
      aria-label={stream.name}
      aria-busy={busy}
      className={cn('rounded-xl border p-4', stream.has_draft && 'border-amber-300 bg-amber-50 dark:bg-amber-950/30')}
    >
      <header className="flex flex-wrap items-center gap-2">
        <h2 className="font-semibold">
          {stream.name}
          <span className="ml-2 text-sm font-normal text-muted-foreground">
            #{stream.position} · stream {stream.id}
          </span>
        </h2>
        {stream.has_draft && <Badge variant="outline">Черновик</Badge>}
        {stream.has_conflicts && <Badge variant="destructive">Конфликты с Keitaro</Badge>}
      </header>

      {stream.offers.length > 0 && (
        <Table className="mt-3">
          <TableHeader>
            <TableRow>
              <TableHead>Оффер</TableHead>
              <TableHead>Share</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {stream.offers.map((offer) => (
              <OfferRow key={offer.offer_id} streamId={stream.id} offer={offer} disabled={busy} />
            ))}
          </TableBody>
        </Table>
      )}

      {stream.offers.length > 0 && (
        <footer className="mt-3 flex flex-wrap items-center justify-end gap-2">
          <div className="mr-auto flex flex-1">
            <AddOffer streamId={streamId} disabled={busy} />
          </div>
          {hasMarks && (
            <Button variant="ghost" disabled={busy} onClick={() => act({ kind: 'acknowledge', streamId })}>
              Понятно
            </Button>
          )}
          {stream.has_conflicts && (
            <>
              <Button variant="outline" disabled={busy} onClick={() => act({ kind: 'resolveAll', streamId, keep: 'mine' })}>
                Всё моё
              </Button>
              <Button variant="outline" disabled={busy} onClick={() => act({ kind: 'resolveAll', streamId, keep: 'keitaro' })}>
                Всё из Keitaro
              </Button>
            </>
          )}
          <Button variant="outline" disabled={busy || !stream.has_draft} onClick={() => act({ kind: 'cancel', streamId })}>
            Cancel
          </Button>
          <Button
            disabled={busy || !stream.has_draft || stream.has_conflicts}
            title={stream.has_conflicts ? 'Сначала решите конфликты с Keitaro' : undefined}
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
  const target = { streamId, offerId: offer.offer_id }

  return (
    <TableRow className={removed ? 'text-muted-foreground opacity-60' : undefined}>
      <TableCell>
        <div className="font-medium">{offer.offer_name}</div>
        <div className="text-xs text-muted-foreground">id {offer.offer_id}</div>
        <KeitaroMark offer={offer} />
        <ConflictChoice streamId={streamId} offer={offer} disabled={disabled} />
      </TableCell>
      <TableCell>
        <ShareCell streamId={streamId} offer={offer} disabled={disabled} />
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
