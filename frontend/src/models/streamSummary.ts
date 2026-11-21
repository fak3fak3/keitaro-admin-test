import type { Stream } from '@/api/streams'

export type StreamSummary = {
  /** Сумма долей активных офферов. */
  total: number
  /** Постоянные предупреждения потока: показываются на потоке, Push не блокируют. */
  warnings: string[]
  /** Офферов с неопубликованными изменениями. */
  changes: number
  conflicts: number
  /** Офферов с пометкой «изменено в Keitaro». */
  marks: number
}

/** Сводка потока для карточки. Единственное место, где фронт выводит предупреждения: когда бэкенд
 * начнёт отдавать их сам, источник меняется здесь. */
export function streamSummary(stream: Stream): StreamSummary {
  const active = stream.offers.filter((offer) => offer.status === 'active')
  const total = active.reduce((sum, offer) => sum + offer.share, 0)
  const warnings =
    active.length > 0 && total !== 100
      ? [`Сумма долей ${total}%, а не 100%: Keitaro распределит трафик по этим долям как есть`]
      : []

  return {
    total,
    warnings,
    changes: stream.offers.filter((offer) => offer.changed).length,
    conflicts: stream.offers.filter((offer) => offer.conflict).length,
    marks: stream.offers.filter((offer) => offer.keitaro_change !== null).length,
  }
}
