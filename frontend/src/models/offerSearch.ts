import { concurrency, createQuery } from '@farfetched/core'
import { createEvent, createStore, sample } from 'effector'
import { debounce } from 'patronum'

import type { Schemas } from '@/api/client'
import { errorText } from '@/api/errors'
import { searchOffersFx } from '@/api/offers'

type Offer = Schemas['OfferOut']

const TYPING_PAUSE_MS = 300

/** Автокомплит офферов Keitaro: форма создания кампании и Add в редакторе. */
export function createOfferSearch() {
  const textChanged = createEvent<string>()
  const offerSelected = createEvent<Offer>()
  const reset = createEvent()

  const $selected = createStore<Offer | null>(null)
    .on(offerSelected, (_, offer) => offer)
    .reset(textChanged, reset) // снова печатают — выбор больше не соответствует полю
  const $text = createStore('')
    .on(textChanged, (_, text) => text)
    .on(offerSelected, (_, offer) => offerLabel(offer))
    .reset(reset)

  const query = createQuery({ effect: searchOffersFx, initialData: [] })
  concurrency(query, { strategy: 'TAKE_LATEST' }) // ответ на устаревший текст отбрасывается

  sample({
    clock: debounce(textChanged, TYPING_PAUSE_MS),
    fn: (text) => text.trim(),
    target: query.start,
  })

  return {
    textChanged,
    offerSelected,
    reset,
    $text,
    $selected,
    $options: query.$data,
    $pending: query.$pending,
    $error: query.$error.map((error) => (error ? errorText(error) : null)),
  }
}

export function offerLabel(offer: Offer): string {
  return `${offer.id} — ${offer.name}`
}

export type OfferSearch = ReturnType<typeof createOfferSearch>
