import { useUnit } from 'effector-react'

import type { StreamOffer } from '@/api/streams'
import { Button } from '@/components/ui/button'
import { actionRequested } from '@/models/editor'

/** Что изменилось в Keitaro с прошлой загрузки (пометка после Fetch). */
export function KeitaroMark({ offer }: { offer: StreamOffer }) {
  if (offer.keitaro_change === null) return null
  const text = {
    share_changed: `изменено в Keitaro: ${offer.keitaro_share_before}% → ${offer.published_share}%`,
    added: 'добавлен в Keitaro',
    removed: 'удалён в Keitaro',
  }[offer.keitaro_change]
  return (
    <div className="mt-1 inline-flex rounded bg-sky-100 px-1.5 py-0.5 text-xs text-sky-800 dark:bg-sky-950 dark:text-sky-300">
      {text}
    </div>
  )
}

/** Оффер изменён и у нас, и в Keitaro: показываем обе версии и даём выбрать. */
export function ConflictChoice({ streamId, offer, disabled }: { streamId: number; offer: StreamOffer; disabled: boolean }) {
  const act = useUnit(actionRequested)
  if (!offer.conflict) return null

  const mine = offer.status === 'removed' ? 'удалён' : `${offer.share}%`
  const theirs = offer.published_status === 'removed' ? 'удалён' : `${offer.published_share}%`
  const resolve = (keep: 'mine' | 'keitaro') =>
    act({ kind: 'resolve', streamId, offerId: offer.offer_id, keep })

  return (
    <div className="mt-1 flex flex-wrap items-center gap-2 rounded bg-amber-100 px-1.5 py-1 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
      <span>Конфликт: у нас {mine}, в Keitaro {theirs}</span>
      <Button variant="outline" size="xs" disabled={disabled} onClick={() => resolve('mine')}>Моё</Button>
      <Button variant="outline" size="xs" disabled={disabled} onClick={() => resolve('keitaro')}>Keitaro</Button>
    </div>
  )
}
