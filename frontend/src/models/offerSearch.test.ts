import { allSettled, fork } from 'effector'

import { ApiError } from '@/api/client'
import { searchOffersFx } from '@/api/offers'

import { createOfferSearch } from './offerSearch'

const MIAFLOW = { id: 3749, name: 'Miaflow 0009' }

test('ввод текста после паузы загружает офферы по запросу', async () => {
  const search = createOfferSearch()
  const requests: string[] = []
  const scope = fork({
    handlers: [[searchOffersFx, async (q: string) => { requests.push(q); return [MIAFLOW] }]],
  })

  await allSettled(search.textChanged, { scope, params: 'mia' })

  expect(requests).toEqual(['mia'])
  expect(scope.getState(search.$text)).toBe('mia')
  expect(scope.getState(search.$options)).toEqual([MIAFLOW])
})

test('опоздавший ответ на старый запрос не затирает новый', async () => {
  const search = createOfferSearch()
  const OLD = [{ id: 1, name: 'mia — устарело' }]
  const NEW = [MIAFLOW]
  let releaseOld: (() => void) | undefined
  const scope = fork({
    handlers: [[searchOffersFx, (q: string) => q === 'mia'
      ? new Promise((resolve) => { releaseOld = () => resolve(OLD) })
      : Promise.resolve(NEW)]],
  })

  const typedOld = allSettled(search.textChanged, { scope, params: 'mia' })
  await vi.waitFor(() => expect(releaseOld).toBeDefined())
  const typedNew = allSettled(search.textChanged, { scope, params: 'miaf' })
  await vi.waitFor(() => expect(scope.getState(search.$options)).toEqual(NEW))
  releaseOld!()
  await Promise.all([typedOld, typedNew])

  expect(scope.getState(search.$options)).toEqual(NEW)
})

test('выбор оффера запоминается и сбрасывается при новом вводе', async () => {
  const search = createOfferSearch()
  const scope = fork({ handlers: [[searchOffersFx, async () => [MIAFLOW]]] })

  await allSettled(search.offerSelected, { scope, params: MIAFLOW })
  expect(scope.getState(search.$selected)).toEqual(MIAFLOW)
  expect(scope.getState(search.$text)).toBe('3749 — Miaflow 0009')

  await allSettled(search.textChanged, { scope, params: 'fito' })
  expect(scope.getState(search.$selected)).toBeNull()
})

test('ошибка поиска — сообщение, а не пустой результат', async () => {
  const search = createOfferSearch()
  const scope = fork({
    handlers: [[searchOffersFx, async () => {
      throw new ApiError(502, 'Keitaro API error (401): Invalid API key')
    }]],
  })

  await allSettled(search.textChanged, { scope, params: '18813' })

  expect(scope.getState(search.$error)).toBe('Keitaro API error (401): Invalid API key')
})
