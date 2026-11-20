import { createQuery } from '@farfetched/core'
import { createEvent, sample } from 'effector'

import { listCampaignsFx } from '@/api/campaigns'

export const campaignsPageOpened = createEvent()

export const campaignsQuery = createQuery({ effect: listCampaignsFx, initialData: [] })

sample({ clock: campaignsPageOpened, target: campaignsQuery.start })

export const $campaigns = campaignsQuery.$data
export const $campaignsError = campaignsQuery.$error.map((error) => error?.message ?? null)
export const $campaignsPending = campaignsQuery.$pending
