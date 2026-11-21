import { createQuery } from '@farfetched/core'
import { createEvent, sample } from 'effector'

import { listCampaignsFx } from '@/api/campaigns'
import { errorText } from '@/api/errors'

export const campaignsPageOpened = createEvent()

export const campaignsQuery = createQuery({ effect: listCampaignsFx, initialData: [] })

sample({ clock: campaignsPageOpened, target: campaignsQuery.start })

export const $campaigns = campaignsQuery.$data
export const $campaignsError = campaignsQuery.$error.map((error) => (error ? errorText(error) : null))
export const $campaignsPending = campaignsQuery.$pending
