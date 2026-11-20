import createClient from 'openapi-fetch'

import type { components, paths } from './schema'

export type Schemas = components['schemas']

/** Ошибка нашего API: статус и сообщение для пользователя из `{"detail": "..."}`. */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function createApi(fetchImpl?: typeof fetch) {
  // API на том же адресе, что и фронт (в dev — через прокси Vite, в Docker — через nginx)
  return createClient<paths>({ baseUrl: window.location.origin, fetch: fetchImpl })
}

type ApiResult<T> = { data?: T; error?: unknown; response: Response }

export async function unwrap<T>(request: Promise<ApiResult<T>>): Promise<T> {
  const { data, error, response } = await request
  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(error, response.status))
  }
  return data as T
}

function errorMessage(error: unknown, status: number): string {
  const detail = (error as { detail?: unknown } | undefined)?.detail
  return typeof detail === 'string' ? detail : `Ошибка сервера (${status})`
}
