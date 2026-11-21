import { render, screen } from '@testing-library/react'
import { fork } from 'effector'
import { Provider } from 'effector-react'
import { MemoryRouter } from 'react-router'

import { listCampaignsFx } from '@/api/campaigns'

import { AppRoutes } from './App'

test('на главной — список кампаний', async () => {
  const scope = fork({ handlers: [[listCampaignsFx, async () => []]] })

  render(
    <Provider value={scope}>
      <MemoryRouter initialEntries={['/']}>
        <AppRoutes />
      </MemoryRouter>
    </Provider>,
  )

  expect(await screen.findByRole('heading', { name: 'Кампании' })).toBeInTheDocument()
  expect(screen.getByText('New campaign')).toBeInTheDocument()
})
