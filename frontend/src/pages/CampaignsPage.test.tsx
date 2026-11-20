import { render, screen } from '@testing-library/react'
import { fork } from 'effector'
import { Provider } from 'effector-react'
import { MemoryRouter } from 'react-router'

import { listCampaignsFx } from '@/api/campaigns'
import { ApiError } from '@/api/client'

import { CampaignsPage } from './CampaignsPage'

function renderPage(handler: () => Promise<unknown>) {
  const scope = fork({ handlers: [[listCampaignsFx, handler]] })
  render(
    <Provider value={scope}>
      <MemoryRouter>
        <CampaignsPage />
      </MemoryRouter>
    </Provider>,
  )
}

test('показывает кампании со ссылкой на редактор', async () => {
  renderPage(async () => [
    {
      keitaro_id: 217109,
      name: 'test_mirolyubov_campaign1',
      alias: 'test-mirolyubov-campaign1-abc123',
      geo: ['AU', 'MX'],
      offer_id: 18813,
      url: 'https://kylovoa.com/test-mirolyubov-campaign1-abc123',
    },
  ])

  const link = await screen.findByRole('link', { name: 'test_mirolyubov_campaign1' })
  expect(link).toHaveAttribute('href', '/campaigns/217109')
  expect(screen.getByText('AU, MX')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'https://kylovoa.com/test-mirolyubov-campaign1-abc123' }))
    .toHaveAttribute('href', 'https://kylovoa.com/test-mirolyubov-campaign1-abc123')
})

test('показывает ошибку загрузки', async () => {
  renderPage(async () => {
    throw new ApiError(502, 'Keitaro API error (401): Unauthorized')
  })

  expect(await screen.findByRole('alert')).toHaveTextContent('Keitaro API error (401): Unauthorized')
})

test('пустой список — подсказка', async () => {
  renderPage(async () => [])

  expect(await screen.findByText('Кампаний пока нет')).toBeInTheDocument()
})
