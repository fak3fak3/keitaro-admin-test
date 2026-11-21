import { ApiError } from './client'

/** Текст ошибки для пользователя: сообщение нашего API или «нет связи». */
export function errorText(error: unknown): string {
  return error instanceof ApiError ? error.message : 'Не удалось связаться с сервером'
}
