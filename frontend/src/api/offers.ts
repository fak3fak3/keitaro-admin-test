import { createEffect } from 'effector'

import { unwrap } from './client'
import { api } from './index'

export const searchOffersFx = createEffect((q: string) =>
  unwrap(api.GET('/api/offers', { params: { query: { q } } })),
)
