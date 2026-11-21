import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { allSettled, fork } from 'effector'
import { Provider } from 'effector-react'
import { MemoryRouter } from 'react-router'

import { listCampaignsFx } from '@/api/campaigns'
import { ApiError } from '@/api/client'
import { searchOffersFx } from '@/api/offers'
import { fetchStreamsFx, listStreamsFx, streamActionFx, type Stream } from '@/api/streams'
import { AppRoutes } from '@/App'
import {
  connectLiveFx,
  disconnectLiveFx,
  liveConnected,
  liveErrorReceived,
  liveStreamsReceived,
} from '@/models/editor'
import { GEO, OFFERS, offer, stream } from '@/test/streams'

type Handlers = {
  streams?: Stream[]
  action?: (action: unknown) => Promise<Stream>
  fetch?: () => Promise<Stream[]>
  list?: () => Promise<Stream[]>
}

function openEditor({ streams = [GEO, OFFERS], action, fetch, list }: Handlers = {}) {
  const sent: unknown[] = []
  const live = { connected: [] as number[], disconnected: 0 }
  const scope = fork({
    handlers: [
      [connectLiveFx, (id: number) => { live.connected.push(id) }],
      [disconnectLiveFx, () => { live.disconnected += 1 }],
      [listStreamsFx, list ?? (async () => streams)],
      [listCampaignsFx, async () => [CAMPAIGN]],
      [fetchStreamsFx, fetch ?? (async () => streams)],
      [streamActionFx, async (a: unknown) => { sent.push(a); return action!(a) }],
      [searchOffersFx, async () => [{ id: 11112, name: 'Oxys' }]],
    ],
  })
  const view = render(
    <Provider value={scope}>
      <MemoryRouter initialEntries={['/campaigns/217109']}>
        <AppRoutes />
      </MemoryRouter>
    </Provider>,
  )
  return { sent, live, scope, view, user: userEvent.setup() }
}

const CAMPAIGN = {
  keitaro_id: 217109,
  name: 'test_mirolyubov_campaign1',
  alias: 'test-mirolyubov-campaign1',
  geo: ['AU'],
  offer_id: 18813,
  url: 'https://kylovoa.com/test-mirolyubov-campaign1',
}

const row = (name: string) => screen.getByRole('row', { name: new RegExp(name) })

test('редактор показывает потоки: без офферов — только заголовок, с офферами — таблица', async () => {
  openEditor()

  expect(await screen.findByRole('heading', { name: /Geo AU → Google/ })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: /Offers/ })).toBeInTheDocument()
  expect(screen.getAllByRole('table')).toHaveLength(1)
  expect(within(row('Offer 3749')).getByRole('button', { name: '34%' })).toBeInTheDocument()
  expect(within(row('Offer 3717')).getByRole('button', { name: '33%' })).toBeInTheDocument()
})

test('Remove: оффер сереет и получает Bring back', async () => {
  const afterRemove = stream(OFFERS.id, [
    offer(3749, 50, { changed: true }),
    offer(3717, 0, { status: 'removed', changed: true }),
    offer(11111, 50, { changed: true }),
  ], { has_draft: true })
  const { sent, user } = openEditor({ action: async () => afterRemove })

  await user.click(within(await screen.findByRole('row', { name: /Offer 3717/ })).getByRole('button', { name: 'Remove' }))

  expect(sent).toEqual([{ kind: 'remove', streamId: OFFERS.id, offerId: 3717 }])
  expect(await within(row('Offer 3717')).findByRole('button', { name: 'Bring back' })).toBeInTheDocument()
  expect(within(row('Offer 3749')).getByRole('button', { name: '50%' })).toBeInTheDocument()
})

test('потоков ещё нет — подсказка, Fetch загружает их из Keitaro', async () => {
  const { user } = openEditor({ streams: [], fetch: async () => [GEO, OFFERS] })

  expect(await screen.findByText(/Нажмите Fetch streams from KT/)).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Fetch streams from KT' }))

  expect(await screen.findByRole('heading', { name: /Offers/ })).toBeInTheDocument()
})

test('ошибка показывается и закрывается', async () => {
  const { user } = openEditor({ fetch: async () => { throw new ApiError(502, 'Keitaro API error (401): Invalid API key') } })

  await user.click(await screen.findByRole('button', { name: 'Fetch streams from KT' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Keitaro API error (401): Invalid API key')

  await user.click(screen.getByRole('button', { name: 'Закрыть' }))
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})

test('без черновика Push и Cancel недоступны', async () => {
  openEditor({ streams: [OFFERS] })

  const card = await screen.findByRole('article')
  expect(within(card).getByRole('button', { name: 'Push to KT' })).toBeDisabled()
  expect(within(card).getByRole('button', { name: 'Cancel' })).toBeDisabled()
})

test('поток с черновиком помечен, Push отправляет его', async () => {
  const draft = stream(OFFERS.id, OFFERS.offers, { has_draft: true })
  const { sent, user } = openEditor({ streams: [draft], action: async () => OFFERS })

  const card = await screen.findByRole('article')
  expect(within(card).getByText(/^Черновик/)).toBeInTheDocument()
  await user.click(within(card).getByRole('button', { name: 'Push to KT' }))

  expect(sent).toEqual([{ kind: 'push', streamId: OFFERS.id }])
  expect(await within(card).findByRole('button', { name: 'Push to KT' })).toBeDisabled()
})

test('пин: закрепить и открепить долю', async () => {
  const pinned = stream(OFFERS.id, [offer(3749, 34), offer(3717, 33, { pinned: true }), offer(11111, 33)])
  const { sent, user } = openEditor({ streams: [pinned] })

  await user.click(within(await screen.findByRole('row', { name: /Offer 3749/ })).getByRole('button', { name: 'Закрепить долю' }))
  await user.click(within(row('Offer 3717')).getByRole('button', { name: 'Открепить долю' }))

  expect(sent).toEqual([
    { kind: 'pin', streamId: OFFERS.id, offerId: 3749 },
    { kind: 'unpin', streamId: OFFERS.id, offerId: 3717 },
  ])
})

test('ручная доля: клик по проценту, ввод, Enter', async () => {
  const { sent, user } = openEditor({ streams: [OFFERS], action: async () => OFFERS })

  await user.click(within(await screen.findByRole('row', { name: /Offer 3717/ })).getByRole('button', { name: '33%' }))
  const input = within(row('Offer 3717')).getByRole('spinbutton', { name: 'Доля оффера 3717, %' })
  await user.clear(input)
  await user.type(input, '50{Enter}')

  expect(sent).toEqual([{ kind: 'share', streamId: OFFERS.id, offerId: 3717, share: 50 }])
})

test('ручная доля: Escape отменяет ввод', async () => {
  const { sent, user } = openEditor({ streams: [OFFERS] })

  await user.click(within(await screen.findByRole('row', { name: /Offer 3717/ })).getByRole('button', { name: '33%' }))
  await user.type(within(row('Offer 3717')).getByRole('spinbutton'), '9{Escape}')

  expect(sent).toEqual([])
  expect(within(row('Offer 3717')).getByRole('button', { name: '33%' })).toBeInTheDocument()
})

test('пометки изменений из Keitaro и «Понятно»', async () => {
  const marked = stream(OFFERS.id, [
    offer(3749, 60, { keitaro_change: 'share_changed', keitaro_share_before: 34 }),
    offer(3717, 0, { status: 'removed', published_status: 'removed', published_share: 0, keitaro_change: 'removed', keitaro_share_before: 33 }),
    offer(11112, 40, { keitaro_change: 'added' }),
  ])
  const { sent, user } = openEditor({ streams: [marked], action: async () => OFFERS })

  expect(await within(await screen.findByRole('row', { name: /Offer 3749/ })).findByText('изменено в Keitaro: 34% → 60%')).toBeInTheDocument()
  expect(within(row('Offer 3717')).getByText('удалён в Keitaro')).toBeInTheDocument()
  expect(within(row('Offer 11112')).getByText('добавлен в Keitaro')).toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Скрыть пометки' }))
  expect(sent).toEqual([{ kind: 'acknowledge', streamId: OFFERS.id }])
})

const CONFLICTED = stream(OFFERS.id, [
  // у нас 50%, в Keitaro за это время стало 60%
  offer(3749, 50, { changed: true, conflict: true, published_share: 60, keitaro_change: 'share_changed', keitaro_share_before: 34 }),
  offer(3717, 0, { status: 'removed', changed: true }),
  // у нас 50%, в Keitaro оффер удалили
  offer(11111, 50, { changed: true, conflict: true, published_status: 'removed', published_share: 0, keitaro_change: 'removed', keitaro_share_before: 33 }),
], { has_draft: true, has_conflicts: true })

test('конфликт решается на каждом оффере: моё или из Keitaro', async () => {
  const { sent, user } = openEditor({ streams: [CONFLICTED], action: async () => CONFLICTED })

  const first = await screen.findByRole('row', { name: /Offer 3749/ })
  expect(within(first).getByText('Конфликт: у нас 50%, в Keitaro 60%')).toBeInTheDocument()
  expect(within(row('Offer 11111')).getByText('Конфликт: у нас 50%, в Keitaro удалён')).toBeInTheDocument()

  await user.click(within(first).getByRole('button', { name: 'Keitaro' }))
  await user.click(within(row('Offer 11111')).getByRole('button', { name: 'Моё' }))

  expect(sent).toEqual([
    { kind: 'resolve', streamId: OFFERS.id, offerId: 3749, keep: 'keitaro' },
    { kind: 'resolve', streamId: OFFERS.id, offerId: 11111, keep: 'mine' },
  ])
})

test('при конфликтах Push недоступен, есть «Всё моё» и «Всё из Keitaro»', async () => {
  const { sent, user } = openEditor({ streams: [CONFLICTED], action: async () => CONFLICTED })

  const card = await screen.findByRole('article')
  expect(within(card).getByRole('button', { name: 'Push to KT' })).toBeDisabled()
  await user.click(within(card).getByRole('button', { name: 'Всё из Keitaro' }))
  await user.click(within(card).getByRole('button', { name: 'Всё моё' }))

  expect(sent).toEqual([
    { kind: 'resolveAll', streamId: OFFERS.id, keep: 'keitaro' },
    { kind: 'resolveAll', streamId: OFFERS.id, keep: 'mine' },
  ])
})

test('пока у потока идёт запрос, кнопки офферов заблокированы', async () => {
  let finish: (() => void) | undefined
  const { user } = openEditor({
    streams: [OFFERS],
    action: () => new Promise((resolve) => { finish = () => resolve(OFFERS) }),
  })

  await user.click(within(await screen.findByRole('row', { name: /Offer 3717/ })).getByRole('button', { name: 'Remove' }))

  expect(within(row('Offer 3749')).getByRole('button', { name: 'Remove' })).toBeDisabled()
  expect(within(row('Offer 3749')).getByRole('button', { name: '34%' })).toBeDisabled()
  finish!()
  await vi.waitFor(() => expect(within(row('Offer 3749')).getByRole('button', { name: 'Remove' })).toBeEnabled())
})

test('Add: поиск оффера под потоком и добавление', async () => {
  const withFour = stream(OFFERS.id, [
    offer(3749, 25, { changed: true }), offer(3717, 25, { changed: true }), offer(11111, 25, { changed: true }),
    offer(11112, 25, { published_status: null, published_share: null, changed: true }),
  ], { has_draft: true })
  const { sent, user } = openEditor({ streams: [OFFERS], action: async () => withFour })

  const card = await screen.findByRole('article')
  await user.click(within(card).getByRole('button', { name: 'Add offer' }))
  await user.type(within(card).getByRole('combobox', { name: 'Оффер для добавления' }), 'oxy')
  await user.click(await within(card).findByRole('option', { name: '11112 — Oxys' }))
  await user.click(within(card).getByRole('button', { name: 'Add' }))

  expect(sent).toEqual([{ kind: 'add', streamId: OFFERS.id, offerId: 11112 }])
  expect(await within(card).findByRole('row', { name: /Offer 11112/ })).toBeInTheDocument()
  expect(within(card).queryByRole('combobox')).not.toBeInTheDocument()
})

test('ручная доля: введённое число заменяет текущее, а не дописывается к нему', async () => {
  const { sent, user } = openEditor({ streams: [OFFERS], action: async () => OFFERS })

  await user.click(within(await screen.findByRole('row', { name: /Offer 3717/ })).getByRole('button', { name: '33%' }))
  await user.keyboard('50{Enter}')

  expect(sent).toEqual([{ kind: 'share', streamId: OFFERS.id, offerId: 3717, share: 50 }])
})

test('ручная доля вне 0–100 не отправляется, поле остаётся открытым с ошибкой', async () => {
  const { sent, user } = openEditor({ streams: [OFFERS] })

  await user.click(within(await screen.findByRole('row', { name: /Offer 3717/ })).getByRole('button', { name: '33%' }))
  await user.keyboard('150{Enter}')

  expect(sent).toEqual([])
  const input = within(row('Offer 3717')).getByRole('spinbutton', { name: 'Доля оффера 3717, %' })
  expect(input).toHaveAttribute('aria-invalid', 'true')
  expect(within(row('Offer 3717')).getByText('Доля — целое число от 0 до 100')).toBeInTheDocument()
})


test('live: индикатор соединения и потоки, пришедшие из Keitaro', async () => {
  const { live, scope } = openEditor({ streams: [OFFERS] })
  expect(await screen.findByText('Подключение…')).toBeInTheDocument()
  expect(live.connected).toEqual([217109])

  await act(() => allSettled(liveConnected, { scope }))
  expect(screen.getByText('Live')).toBeInTheDocument()

  const changed = stream(OFFERS.id, [offer(3749, 60, { keitaro_change: 'share_changed', keitaro_share_before: 34 })])
  await act(() => allSettled(liveStreamsReceived, { scope, params: [changed] }))
  expect(screen.getByText('изменено в Keitaro: 34% → 60%')).toBeInTheDocument()
})

test('live: уход со страницы закрывает соединение', async () => {
  const { live, view } = openEditor({ streams: [OFFERS] })
  await screen.findByRole('article')

  view.unmount()

  expect(live.disconnected).toBe(1)
})

/* ---------- Редизайн (docs/UX.md): состояния потока видны на самом потоке ---------- */

const card = (name: string) => screen.findByRole('article', { name })

test('ошибка действия показывается на своём потоке, а не над страницей, и закрывается', async () => {
  const pinError = 'Закреплено 20%, а остаток 80% некому отдать: все активные офферы закреплены'
  const { user } = openEditor({ action: async () => { throw new ApiError(422, pinError) } })

  await user.click(within(await screen.findByRole('row', { name: /Offer 3749/ })).getByRole('button', { name: 'Закрепить долю' }))

  const offers = await card('Offers')
  expect(await within(offers).findByRole('alert')).toHaveTextContent(pinError)
  expect(within(await card('Geo AU → Google')).queryByRole('alert')).not.toBeInTheDocument()

  await user.click(within(offers).getByRole('button', { name: 'Закрыть' }))
  expect(within(offers).queryByRole('alert')).not.toBeInTheDocument()
})

test('сумма долей не 100% — предупреждение на потоке, Push черновика не блокируется', async () => {
  const odd = stream(OFFERS.id, [offer(3749, 20, { pinned: true, changed: true }), offer(3717, 0, { status: 'removed', changed: true })], { has_draft: true })
  openEditor({ streams: [odd] })

  const offers = await card('Offers')
  expect(within(offers).getByText(/Сумма долей 20%, а не 100%/)).toBeInTheDocument()
  expect(within(offers).getByRole('row', { name: /Итого/ })).toHaveTextContent('20%')
  expect(within(offers).getByRole('button', { name: 'Push to KT' })).toBeEnabled()
})

test('итоговая сумма активных долей под таблицей', async () => {
  openEditor({ streams: [OFFERS] })

  expect(within(await card('Offers')).getByRole('row', { name: /Итого/ })).toHaveTextContent('100%')
  expect(screen.queryByText(/а не 100%/)).not.toBeInTheDocument()
})

test('черновик: число изменений, прежняя доля у изменённого оффера, метка нового', async () => {
  const draft = stream(OFFERS.id, [
    offer(3749, 25, { changed: true, published_share: 34 }),
    offer(3717, 75),
    offer(11112, 0, { changed: true, published_status: null, published_share: null }),
  ], { has_draft: true })
  openEditor({ streams: [draft] })

  const offers = await card('Offers')
  expect(within(offers).getByText('Черновик · 2 изменения')).toBeInTheDocument()
  expect(within(row('Offer 3749')).getByText('было 34%')).toBeInTheDocument()
  expect(within(row('Offer 3717')).queryByText(/было/)).not.toBeInTheDocument()
  expect(within(row('Offer 11112')).getByText('новый')).toBeInTheDocument()
})

test('удалённый оффер подписан removed, Bring back доступен', async () => {
  const removed = stream(OFFERS.id, [offer(3749, 100), offer(3717, 0, { status: 'removed', published_status: 'removed', published_share: 0 })])
  openEditor({ streams: [removed] })

  const archived = await screen.findByRole('row', { name: /Offer 3717/ })
  expect(within(archived).getByText('removed')).toBeInTheDocument()
  expect(within(archived).getByRole('button', { name: 'Bring back' })).toBeEnabled()
})

test('конфликты: пояснение на потоке, почему Push недоступен', async () => {
  openEditor({ streams: [CONFLICTED] })

  const offers = await card('Offers')
  expect(within(offers).getByText(/2 оффера изменены и у нас, и в Keitaro/)).toBeInTheDocument()
  expect(within(offers).getByText(/Push недоступен, пока не выбрана версия/)).toBeInTheDocument()
})

test('пометки Keitaro: пояснение на потоке и «Скрыть пометки»', async () => {
  const marked = stream(OFFERS.id, [offer(3749, 60, { keitaro_change: 'share_changed', keitaro_share_before: 34 }), offer(3717, 40)])
  const { sent, user } = openEditor({ streams: [marked], action: async () => OFFERS })

  const offers = await card('Offers')
  expect(within(offers).getByText(/С прошлой загрузки в Keitaro изменился 1 оффер/)).toBeInTheDocument()
  await user.click(within(offers).getByRole('button', { name: 'Скрыть пометки' }))

  expect(sent).toEqual([{ kind: 'acknowledge', streamId: OFFERS.id }])
})

test('поток без офферов поясняет, что редактируется в Keitaro', async () => {
  openEditor({ streams: [GEO] })

  expect(within(await card('Geo AU → Google')).getByText(/Офферов нет/)).toBeInTheDocument()
})

test('пока потоки грузятся — индикатор загрузки', async () => {
  openEditor({ streams: [OFFERS], list: () => new Promise(() => {}) })

  expect(await screen.findByText('Загружаем потоки…')).toBeInTheDocument()
})

test('live: ошибка Keitaro — плашка над потоками с последствием', async () => {
  const { scope } = openEditor({ streams: [OFFERS] })
  await card('Offers')

  await act(() => allSettled(liveErrorReceived, { scope, params: 'Keitaro API error (401): Invalid API key' }))

  expect(screen.getByRole('status')).toHaveTextContent(/Keitaro не отвечает — изменения из трекера не приходят/)
  expect(screen.getByRole('status')).toHaveTextContent('Keitaro API error (401): Invalid API key')
})

test('в крошках — имя кампании из нашего списка', async () => {
  openEditor({ streams: [OFFERS] })

  const crumbs = await screen.findByRole('navigation', { name: 'Хлебные крошки' })
  expect(await within(crumbs).findByText('test_mirolyubov_campaign1')).toBeInTheDocument()
})
