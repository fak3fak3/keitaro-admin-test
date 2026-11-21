import type { Stream } from './streams'

export type LiveHandlers = {
  /** Потоки кампании после слияния с Keitaro (приходят, когда в Keitaro что-то изменилось). */
  streams: (streams: Stream[]) => void
  /** Keitaro ответил ошибкой; соединение с нашим бэкендом при этом живо. */
  error: (detail: string) => void
  open: () => void
  /** Соединение с бэкендом потеряно; EventSource переподключится сам. */
  lost: () => void
}

/** SSE `/api/campaigns/{id}/live`: пока соединение открыто, бэкенд опрашивает Keitaro. */
export function openLiveConnection(campaignId: number, on: LiveHandlers): () => void {
  const source = new EventSource(`/api/campaigns/${campaignId}/live`)
  source.onopen = () => on.open()
  source.onerror = () => on.lost()
  source.addEventListener('streams', (event) => on.streams(JSON.parse(event.data)))
  // не 'error': в браузере это имя занято сетевыми ошибками EventSource (onerror)
  source.addEventListener('keitaro_error', (event) => on.error(JSON.parse(event.data).detail))
  return () => source.close()
}
