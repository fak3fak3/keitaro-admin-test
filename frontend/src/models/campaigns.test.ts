import { allSettled, fork } from 'effector'

import { listCampaignsFx } from '@/api/campaigns'
import { ApiError, type Schemas } from '@/api/client'

import { $campaigns, $campaignsError, campaignsPageOpened } from './campaigns'

const CAMPAIGN: Schemas['CampaignOut'] = {
  keitaro_id: 217109,
  name: 'test_mirolyubov_campaign1',
  alias: 'test-mirolyubov-campaign1-abc123',
  geo: ['AU'],
  offer_id: 18813,
  url: 'https://kylovoa.com/test-mirolyubov-campaign1-abc123',
}

test('открытие страницы загружает кампании', async () => {
  const scope = fork({ handlers: [[listCampaignsFx, async () => [CAMPAIGN]]] })

  await allSettled(campaignsPageOpened, { scope })

  expect(scope.getState($campaigns)).toEqual([CAMPAIGN])
  expect(scope.getState($campaignsError)).toBeNull()
})

test('ошибка загрузки — сообщение для пользователя', async () => {
  const scope = fork({
    handlers: [[listCampaignsFx, async () => { throw new ApiError(502, 'Keitaro API error (401): Unauthorized') }]],
  })

  await allSettled(campaignsPageOpened, { scope })

  expect(scope.getState($campaignsError)).toBe('Keitaro API error (401): Unauthorized')
})
