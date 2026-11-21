import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { fork } from 'effector'
import { Provider } from 'effector-react'
import { MemoryRouter } from 'react-router'

import { createCampaignFx, listCampaignsFx } from '@/api/campaigns'
import { ApiError } from '@/api/client'
import { searchOffersFx } from '@/api/offers'

import { NewCampaignForm } from './NewCampaignForm'

const OFFER = { id: 18813, name: 'Test offer' }
const CREATED = {
  keitaro_id: 500,
  name: 'test_mirolyubov_campaign2',
  alias: 'test-mirolyubov-campaign2-abc123',
  geo: ['MX', 'AU'],
  offer_id: 18813,
  url: 'https://kylovoa.com/test-mirolyubov-campaign2-abc123',
}

function renderForm(create: () => Promise<unknown>) {
  const scope = fork({
    handlers: [
      [createCampaignFx, create],
      [listCampaignsFx, async () => []],
      [searchOffersFx, async () => [OFFER]],
    ],
  })
  render(
    <Provider value={scope}>
      <MemoryRouter>
        <NewCampaignForm />
      </MemoryRouter>
    </Provider>,
  )
}

async function fillAndSubmit() {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Название'), 'test_mirolyubov_campaign2')
  await user.type(screen.getByLabelText('Гео'), 'MX,AU')
  await user.type(screen.getByRole('combobox', { name: 'Оффер' }), 'test')
  await user.click(await screen.findByRole('option', { name: '18813 — Test offer' }))
  await user.click(screen.getByRole('button', { name: 'Создать кампанию' }))
}

test('создание кампании через форму с автокомплитом оффера', async () => {
  renderForm(async () => CREATED)

  await fillAndSubmit()

  expect(await screen.findByText(/Кампания test_mirolyubov_campaign2 создана/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: CREATED.url })).toHaveAttribute('href', CREATED.url)
  expect(screen.getByRole('link', { name: 'Открыть редактор' })).toHaveAttribute('href', '/campaigns/500')
})

test('кнопка неактивна, пока оффер не выбран', async () => {
  renderForm(async () => CREATED)
  const user = userEvent.setup()

  await user.type(screen.getByLabelText('Название'), 'x')
  await user.type(screen.getByLabelText('Гео'), 'MX')

  expect(screen.getByRole('button', { name: 'Создать кампанию' })).toBeDisabled()
})

test('ошибка валидации показывается у поля', async () => {
  renderForm(async () => {
    throw new ApiError(422, 'Проверьте поля формы', { geo: "неверный код страны: 'MXX'" })
  })

  await fillAndSubmit()

  expect(await screen.findByText("неверный код страны: 'MXX'")).toBeInTheDocument()
})
