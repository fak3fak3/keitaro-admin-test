import createClient from 'openapi-fetch'

import type { components, paths } from './schema'

export type Schemas = components['schemas']

/** Ошибка нашего API: статус и сообщение для пользователя из `{"detail": "..."}`. */
export class ApiError extends Error {
  readonly status: number
  /** Ошибки валидации (422) по полям запроса: `{ geo: "неверный код страны: 'Mexico'" }`. */
  readonly fields: Record<string, string>

  constructor(status: number, message: string, fields: Record<string, string> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fields = fields
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
    throw toApiError(response.status, (error as { detail?: unknown } | undefined)?.detail)
  }
  return data as T
}

type ValidationIssue = { loc: (string | number)[]; msg: string }

function toApiError(status: number, detail: unknown): ApiError {
  if (typeof detail === 'string') return new ApiError(status, detail)
  if (Array.isArray(detail)) {
    const fields = Object.fromEntries(
      (detail as ValidationIssue[]).map((issue) => [
        String(issue.loc.at(-1)),
        issue.msg.replace(/^Value error, /, ''),
      ]),
    )
    return new ApiError(status, 'Проверьте поля формы', fields)
  }
  return new ApiError(status, `Ошибка сервера (${status})`)
}
