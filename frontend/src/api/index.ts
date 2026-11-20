import { createApi } from './client'

/** Клиент нашего API для приложения; в тестах эффекты подменяются через `fork({ handlers })`. */
export const api = createApi()
