import { ApiError, createApi, unwrap } from './client'

function respond(status: number, body: unknown) {
  return async () => new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

test('успешный ответ отдаёт данные', async () => {
  const api = createApi(respond(200, [{ id: 1, name: 'Offer' }]))

  await expect(unwrap(api.GET('/api/offers'))).resolves.toEqual([{ id: 1, name: 'Offer' }])
})

test('ошибка бэкенда превращается в ApiError с его сообщением', async () => {
  const api = createApi(respond(409, { detail: 'Решите конфликты с Keitaro по офферам 3749, затем Push' }))

  const error = await unwrap(api.POST('/api/streams/{stream_id}/push', {
    params: { path: { stream_id: 1 } },
  })).catch((e: unknown) => e)

  expect(error).toBeInstanceOf(ApiError)
  expect(error).toMatchObject({
    status: 409,
    message: 'Решите конфликты с Keitaro по офферам 3749, затем Push',
  })
})

test('ошибки валидации (422) раскладываются по полям', async () => {
  const api = createApi(respond(422, {
    detail: [
      { type: 'value_error', loc: ['body', 'geo'], msg: "Value error, неверный код страны: 'Mexico'" },
      { type: 'greater_than', loc: ['body', 'offer_id'], msg: 'Input should be greater than 0' },
    ],
  }))

  const error = await unwrap(api.POST('/api/campaigns', {
    body: { name: 'X', geo: ['Mexico'], offer_id: 0 },
  })).catch((e: unknown) => e)

  expect(error).toMatchObject({
    status: 422,
    message: 'Проверьте поля формы',
    fields: { geo: "неверный код страны: 'Mexico'", offer_id: 'Input should be greater than 0' },
  })
})
