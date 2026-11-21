import { allSettled, fork, type Scope } from 'effector'

import { createCampaignFx, listCampaignsFx } from '@/api/campaigns'
import { ApiError, type Schemas } from '@/api/client'
import { searchOffersFx } from '@/api/offers'

import { $campaigns } from './campaigns'
import {
  $canSubmit,
  $created,
  $fieldErrors,
  $formError,
  $geo,
  $name,
  formSubmitted,
  geoChanged,
  nameChanged,
  offerSearch,
} from './newCampaign'

const OFFER = { id: 18813, name: 'Test offer' }
const CREATED: Schemas['CampaignOut'] = {
  keitaro_id: 500,
  name: 'test_mirolyubov_campaign2',
  alias: 'test-mirolyubov-campaign2-abc123',
  geo: ['MX', 'AU'],
  offer_id: 18813,
  url: 'https://kylovoa.com/test-mirolyubov-campaign2-abc123',
}

async function fillForm(scope: Scope) {
  await allSettled(nameChanged, { scope, params: 'test_mirolyubov_campaign2' })
  await allSettled(geoChanged, { scope, params: 'mx, au' })
  await allSettled(offerSearch.offerSelected, { scope, params: OFFER })
}

test('отправка создаёт кампанию и обновляет список', async () => {
  const sent: unknown[] = []
  const scope = fork({
    handlers: [
      [createCampaignFx, async (body: unknown) => { sent.push(body); return CREATED }],
      [listCampaignsFx, async () => [CREATED]],
      [searchOffersFx, async () => [OFFER]],
    ],
  })
  await fillForm(scope)

  await allSettled(formSubmitted, { scope })

  expect(sent).toEqual([{ name: 'test_mirolyubov_campaign2', geo: ['mx', 'au'], offer_id: 18813 }])
  expect(scope.getState($created)).toEqual(CREATED)
  expect(scope.getState($campaigns)).toEqual([CREATED])
})

function scopeWith(create: (body: unknown) => Promise<unknown>) {
  return fork({
    handlers: [
      [createCampaignFx, create],
      [listCampaignsFx, async () => []],
      [searchOffersFx, async () => [OFFER]],
    ],
  })
}

test('после создания форма очищается', async () => {
  const scope = scopeWith(async () => CREATED)
  await fillForm(scope)

  await allSettled(formSubmitted, { scope })

  expect(scope.getState($name)).toBe('')
  expect(scope.getState($geo)).toBe('')
  expect(scope.getState(offerSearch.$selected)).toBeNull()
  expect(scope.getState(offerSearch.$text)).toBe('')
})

test.each([
  ['без названия', nameChanged, '   '],
  ['без гео', geoChanged, ''],
])('%s отправить нельзя', async (_, event, value) => {
  const scope = scopeWith(async () => { throw new Error('запрос не должен уйти') })
  await fillForm(scope)
  await allSettled(event, { scope, params: value })

  await allSettled(formSubmitted, { scope })

  expect(scope.getState($canSubmit)).toBe(false)
  expect(scope.getState($created)).toBeNull()
})

test('без выбранного оффера отправить нельзя, даже если текст введён', async () => {
  const scope = scopeWith(async () => { throw new Error('запрос не должен уйти') })
  await fillForm(scope)
  await allSettled(offerSearch.textChanged, { scope, params: '18813' })

  await allSettled(formSubmitted, { scope })

  expect(scope.getState($canSubmit)).toBe(false)
})

test('ошибки валидации показываются у полей', async () => {
  const scope = scopeWith(async () => {
    throw new ApiError(422, 'Проверьте поля формы', { geo: "неверный код страны: 'Mexico'" })
  })
  await fillForm(scope)

  await allSettled(formSubmitted, { scope })

  expect(scope.getState($fieldErrors)).toEqual({ geo: "неверный код страны: 'Mexico'" })
  expect(scope.getState($formError)).toBeNull()
  expect(scope.getState($name)).toBe('test_mirolyubov_campaign2') // введённое не теряется
})

test('прочие ошибки — общим сообщением; новая отправка их сбрасывает', async () => {
  let attempt = 0
  const scope = scopeWith(async () => {
    attempt += 1
    if (attempt === 1) throw new ApiError(404, 'Оффер 18813 не найден в Keitaro')
    return CREATED
  })
  await fillForm(scope)

  await allSettled(formSubmitted, { scope })
  expect(scope.getState($formError)).toBe('Оффер 18813 не найден в Keitaro')

  await allSettled(formSubmitted, { scope })
  expect(scope.getState($formError)).toBeNull()
})
