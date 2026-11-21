import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { fork } from 'effector'
import { Provider } from 'effector-react'

import { ApiError } from '@/api/client'
import { searchOffersFx } from '@/api/offers'
import { createOfferSearch } from '@/models/offerSearch'

import { OfferAutocomplete } from './OfferAutocomplete'

test('ошибка поиска показывается в списке вместо «ничего не найдено»', async () => {
  const search = createOfferSearch()
  const scope = fork({
    handlers: [[searchOffersFx, async () => {
      throw new ApiError(502, 'Keitaro API error (401): Invalid API key')
    }]],
  })
  render(
    <Provider value={scope}>
      <OfferAutocomplete search={search} label="Оффер" />
    </Provider>,
  )

  await userEvent.type(screen.getByRole('combobox', { name: 'Оффер' }), '18813')

  expect(await screen.findByText('Keitaro API error (401): Invalid API key')).toBeInTheDocument()
  expect(screen.queryByText('Ничего не найдено')).not.toBeInTheDocument()
})
