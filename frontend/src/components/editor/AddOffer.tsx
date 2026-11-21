import { useUnit } from 'effector-react'

import { OfferAutocomplete } from '@/components/OfferAutocomplete'
import { Button } from '@/components/ui/button'
import {
  $addStreamId,
  addClosed,
  addOfferSearch,
  addOpened,
  addSubmitted,
} from '@/models/editor'

/** Add под таблицей потока: поиск оффера с автокомплитом и кнопка Add (как в видео). */
export function AddOffer({ streamId, disabled }: { streamId: number; disabled: boolean }) {
  const [openStreamId, selected, open, close, submit] = useUnit([
    $addStreamId,
    addOfferSearch.$selected,
    addOpened,
    addClosed,
    addSubmitted,
  ])

  if (openStreamId !== streamId) {
    return (
      <Button variant="outline" disabled={disabled} onClick={() => open(streamId)}>
        Add offer
      </Button>
    )
  }

  return (
    <div className="flex flex-1 flex-wrap items-center gap-2">
      <div className="min-w-64 flex-1">
        <OfferAutocomplete search={addOfferSearch} label="Оффер для добавления" />
      </div>
      <Button disabled={disabled || selected === null} onClick={() => submit()}>
        Add
      </Button>
      <Button variant="ghost" onClick={() => close()}>
        Отмена
      </Button>
    </div>
  )
}
