import { createEffect } from 'effector'

import { unwrap } from './client'
import { api } from './index'

export const listCampaignsFx = createEffect(() => unwrap(api.GET('/api/campaigns')))
