import { createQuery } from '@farfetched/core'
import { combine, createEvent, createStore, sample } from 'effector'

import { connectCampaignFx, listCampaignsFx } from '@/api/campaigns'
import { errorText } from '@/api/errors'
import { createMutation } from '@farfetched/core'

export const campaignsPageOpened = createEvent()
export const connectIdChanged = createEvent<string>()
export const connectSubmitted = createEvent()

export const campaignsQuery = createQuery({ effect: listCampaignsFx, initialData: [] })
export const connectCampaignMutation = createMutation({ effect: connectCampaignFx })
const connected = connectCampaignMutation.finished.success
const connectFailed = connectCampaignMutation.finished.failure.map(({ error }) => error)

export const $connectId = createStore('').on(connectIdChanged, (_, value) => value)
export const $canConnect = combine(
  $connectId,
  connectCampaignMutation.$pending,
  (value, pending) => /^\d+$/.test(value.trim()) && Number(value) > 0 && !pending,
)

sample({
  clock: connectSubmitted,
  source: $connectId,
  filter: $canConnect,
  fn: (value) => ({ keitaro_id: Number(value.trim()) }),
  target: connectCampaignMutation.start,
})
sample({ clock: connected, target: campaignsQuery.start })

export const $connectError = createStore<string | null>(null)
  .on(connectFailed, (_, error) => errorText(error))
  .reset(connectCampaignMutation.start)

sample({ clock: campaignsPageOpened, target: campaignsQuery.start })

export const $campaigns = campaignsQuery.$data
export const $campaignsError = campaignsQuery.$error.map((error) => (error ? errorText(error) : null))
export const $campaignsPending = campaignsQuery.$pending
