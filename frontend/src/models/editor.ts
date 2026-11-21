import { createMutation, createQuery } from '@farfetched/core'
import { combine, createEffect, createEvent, createStore, sample, scopeBind } from 'effector'

import { errorText } from '@/api/errors'
import { openLiveConnection } from '@/api/live'

import {
  fetchStreamsFx,
  listStreamsFx,
  type Stream,
  type StreamAction,
  streamActionFx,
} from '@/api/streams'

import { $campaigns, campaignsQuery } from './campaigns'
import { createOfferSearch } from './offerSearch'

/** Редактор офферов кампании (часть 2 ТЗ). Доли и черновик считает бэкенд — здесь только состояние UI. */
export const editorOpened = createEvent<number>()

export const $campaignId = createStore<number | null>(null).on(editorOpened, (_, id) => id)

export const streamsQuery = createQuery({ effect: listStreamsFx })

sample({ clock: editorOpened, target: streamsQuery.start })

/** Имя для крошек — из нашего списка кампаний; кампания, созданная не через нас, остаётся по id. */
sample({ clock: editorOpened, target: campaignsQuery.start })

export const $campaignName = combine(
  $campaigns,
  $campaignId,
  (campaigns, id) => campaigns.find((campaign) => campaign.keitaro_id === id)?.name ?? null,
)

/** Fetch streams from KT: бэкенд сливает Keitaro с черновиком и возвращает все потоки. */
export const fetchClicked = createEvent()
export const fetchMutation = createMutation({ effect: fetchStreamsFx })

sample({
  clock: fetchClicked,
  source: $campaignId,
  filter: (id): id is number => id !== null,
  target: fetchMutation.start,
})

/** Любая кнопка над потоком или оффером: Add, Remove, Pin, Push, решение конфликта и т.д. */
export const actionRequested = createEvent<StreamAction>()
export const actionMutation = createMutation({ effect: streamActionFx })

/** Потоки с запросом в работе. Ответ — поток целиком, поэтому два параллельных действия над одним
 * потоком могли бы прийти в обратном порядке и затереть друг друга: пока идёт запрос, поток заблокирован. */
export const $busyStreams = createStore<number[]>([])
  .on(actionMutation.start, (busy, { streamId }) => [...busy, streamId])
  .on(actionMutation.finished.finally, (busy, { params }) => busy.filter((id) => id !== params.streamId))

sample({
  clock: actionRequested,
  source: $busyStreams,
  filter: (busy, action) => !busy.includes(action.streamId),
  fn: (_, action) => action,
  target: actionMutation.start,
})

export const $streams = createStore<Stream[]>([])
  .on(streamsQuery.finished.success, (_, { result }) => result)
  .on(fetchMutation.finished.success, (_, { result }) => result)
  .on(actionMutation.finished.success, (streams, { result }) =>
    streams.map((stream) => (stream.id === result.id ? result : stream)),
  )
  .reset(editorOpened) // другая кампания: не показываем чужие потоки, пока грузятся свои

/** Ошибка страницы: загрузка потоков и Fetch относятся ко всей кампании. */
export const errorDismissed = createEvent()
export const $editorError = createStore<string | null>(null)
  .on([streamsQuery.finished.failure, fetchMutation.finished.failure], (_, { error }) => errorText(error))
  .reset(errorDismissed, streamsQuery.start, fetchMutation.start)

/** Ошибки действий — у своего потока (текстом бэкенда); новое действие над потоком снимает его ошибку. */
export const streamErrorDismissed = createEvent<number>()

const withoutStream = (errors: Record<number, string>, streamId: number) =>
  Object.fromEntries(Object.entries(errors).filter(([id]) => Number(id) !== streamId))

export const $streamErrors = createStore<Record<number, string>>({})
  .on(actionMutation.finished.failure, (errors, { params, error }) => ({
    ...errors,
    [params.streamId]: errorText(error),
  }))
  .on(actionMutation.start, (errors, { streamId }) => withoutStream(errors, streamId))
  .on(streamErrorDismissed, withoutStream)
  .reset(editorOpened)

/** Add: поле поиска оффера открыто под одним потоком за раз, модель поиска общая. */
export const addOfferSearch = createOfferSearch()
export const addOpened = createEvent<number>()
export const addClosed = createEvent()
export const addSubmitted = createEvent()

const offerAdded = actionMutation.finished.success.filter({ fn: ({ params }) => params.kind === 'add' })

export const $addStreamId = createStore<number | null>(null)
  .on(addOpened, (_, streamId) => streamId)
  .reset(addClosed, offerAdded, editorOpened)

sample({ clock: [addOpened, addClosed, offerAdded], target: addOfferSearch.reset })

sample({
  clock: addSubmitted,
  source: { streamId: $addStreamId, offer: addOfferSearch.$selected },
  filter: ({ streamId, offer }) => streamId !== null && offer !== null,
  fn: ({ streamId, offer }): StreamAction => ({ kind: 'add', streamId: streamId!, offerId: offer!.id }),
  target: actionRequested,
})

/* ---------- Live: пока открыт редактор, бэкенд опрашивает Keitaro и присылает потоки (SSE) ---------- */

export const editorClosed = createEvent()
export const liveStreamsReceived = createEvent<Stream[]>()
export const liveErrorReceived = createEvent<string>()
export const liveConnected = createEvent()
export const liveLost = createEvent()

let closeLive: (() => void) | null = null

export const connectLiveFx = createEffect((campaignId: number) => {
  closeLive?.() // редактор переоткрыт на другой кампании
  closeLive = openLiveConnection(campaignId, {
    streams: scopeBind(liveStreamsReceived, { safe: true }),
    error: scopeBind(liveErrorReceived, { safe: true }),
    open: scopeBind(liveConnected, { safe: true }),
    lost: scopeBind(liveLost, { safe: true }),
  })
})

export const disconnectLiveFx = createEffect(() => {
  closeLive?.()
  closeLive = null
})

sample({ clock: editorOpened, target: connectLiveFx })
sample({ clock: editorClosed, target: disconnectLiveFx })

$streams.on(liveStreamsReceived, (_, streams) => streams)

export const $liveStatus = createStore<'off' | 'connecting' | 'live' | 'lost'>('off')
  .on(editorOpened, () => 'connecting')
  .on([liveConnected, liveStreamsReceived], () => 'live')
  .on(liveLost, () => 'lost') // EventSource переподключится сам
  .reset(editorClosed)

/** Keitaro ответил ошибкой при опросе; снимается, как только опрос снова прислал потоки. */
export const $liveError = createStore<string | null>(null)
  .on(liveErrorReceived, (_, detail) => detail)
  .reset(liveStreamsReceived, editorOpened, editorClosed)
