import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { fork } from 'effector'
import { Provider } from 'effector-react'
import { MemoryRouter } from 'react-router'

import { connectCampaignFx, listCampaignsFx } from '@/api/campaigns'
import { ApiError } from '@/api/client'
import { searchOffersFx } from '@/api/offers'

import { CampaignsPage } from './CampaignsPage'

function renderPage(
  handler: () => Promise<unknown>,
  connect: (body: unknown) => Promise<unknown> = async () => ({}),
) {
  const scope = fork({
    handlers: [
      [listCampaignsFx, handler],
      [connectCampaignFx, connect],
      [searchOffersFx, async () => []],
    ],
  })
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

test('показывает форму подключения кампании Keitaro по ID', async () => {
  renderPage(async () => [])

  expect(await screen.findByRole('textbox', { name: 'ID кампании Keitaro' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Подключить' })).toBeInTheDocument()
})

test('подключает кампанию по введённому ID и обновляет список', async () => {
  const user = userEvent.setup()
  const connected = {
    keitaro_id: 93212,
    name: 'campaign 2',
    alias: 'campaign-2',
    geo: null,
    offer_id: null,
    url: 'https://kylovoa.com/campaign-2',
  }
  const sent: unknown[] = []
  let listCalls = 0
  renderPage(
    async () => (listCalls++ === 0 ? [] : [connected]),
    async (body: unknown) => { sent.push(body); return connected },
  )

  await user.type(await screen.findByRole('textbox', { name: 'ID кампании Keitaro' }), '93212')
  await user.click(screen.getByRole('button', { name: 'Подключить' }))

  expect(sent).toEqual([{ keitaro_id: 93212 }])
  expect(await screen.findByRole('link', { name: 'campaign 2' })).toHaveAttribute(
    'href',
    '/campaigns/93212',
  )
  expect(screen.getAllByText('—')).toHaveLength(2)
})

test('пока список грузится — индикатор загрузки', async () => {
  renderPage(() => new Promise(() => {}))

  expect(await screen.findByText('Загружаем кампании…')).toBeInTheDocument()
})

test('форма новой кампании открывается кнопкой над списком и закрывается', async () => {
  const user = userEvent.setup()
  renderPage(async () => [])
  await screen.findByText('Кампаний пока нет')
  expect(screen.queryByRole('textbox', { name: 'Название' })).not.toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'New campaign' }))
  expect(screen.getByRole('textbox', { name: 'Название' })).toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Свернуть' }))
  expect(screen.queryByRole('textbox', { name: 'Название' })).not.toBeInTheDocument()
})
