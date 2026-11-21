import { createEffect } from 'effector'

import { type Schemas, unwrap } from './client'
import { api } from './index'

export const listCampaignsFx = createEffect(() => unwrap(api.GET('/api/campaigns')))

export const createCampaignFx = createEffect((body: Schemas['CampaignCreateRequest']) =>
  unwrap(api.POST('/api/campaigns', { body })),
)
