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
