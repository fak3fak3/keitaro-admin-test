import { createMutation } from '@farfetched/core'
import { combine, createEvent, createStore, sample } from 'effector'

import { createCampaignFx } from '@/api/campaigns'
import { ApiError, type Schemas } from '@/api/client'
import { errorText } from '@/api/errors'

import { campaignsQuery } from './campaigns'
import { createOfferSearch } from './offerSearch'

/** Форма «New campaign» (часть 1 ТЗ): Name, Geo, Offer с автокомплитом. */
export const offerSearch = createOfferSearch()

export const nameChanged = createEvent<string>()
export const geoChanged = createEvent<string>()
export const formSubmitted = createEvent()

export const createCampaignMutation = createMutation({ effect: createCampaignFx })
const created = createCampaignMutation.finished.success

export const $name = createStore('').on(nameChanged, (_, name) => name).reset(created)
export const $geo = createStore('').on(geoChanged, (_, geo) => geo).reset(created)

/** Формат гео и прочее проверяет бэкенд (422); здесь — только что всё заполнено и не идёт отправка. */
export const $canSubmit = combine(
  $name,
  $geo,
  offerSearch.$selected,
  createCampaignMutation.$pending,
  (name, geo, offer, pending) => name.trim() !== '' && geo.trim() !== '' && offer !== null && !pending,
)

sample({
  clock: formSubmitted,
  source: { name: $name, geo: $geo, offer: offerSearch.$selected },
  filter: $canSubmit,
  fn: ({ name, geo, offer }) => ({
    name,
    geo: geo.split(',').map((code) => code.trim()),
    offer_id: offer!.id,
  }),
  target: createCampaignMutation.start,
})

export const $created = createStore<Schemas['CampaignOut'] | null>(null)
  .on(created, (_, { result }) => result)

sample({ clock: created, target: [campaignsQuery.start, offerSearch.reset] })

const failed = createCampaignMutation.finished.failure.map(({ error }) => error)

/** 422 — сообщения бэкенда по полям (`name`, `geo`, `offer_id`). */
export const $fieldErrors = createStore<Record<string, string>>({})
  .on(failed, (_, error) => (isValidation(error) ? error.fields : {}))
  .reset(createCampaignMutation.start)

/** Остальные ошибки — одним сообщением над формой. */
export const $formError = createStore<string | null>(null)
  .on(failed, (_, error) => (isValidation(error) ? null : errorText(error)))
  .reset(createCampaignMutation.start)

function isValidation(error: unknown): error is ApiError {
  return error instanceof ApiError && error.status === 422
}
