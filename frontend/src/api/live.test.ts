import { openLiveConnection } from './live'

class FakeEventSource {
  static last: FakeEventSource
  url: string
  closed = false
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  listeners: Record<string, (event: MessageEvent) => void> = {}

  constructor(url: string) {
    this.url = url
    FakeEventSource.last = this
  }
  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners[type] = listener
  }
  close() {
    this.closed = true
  }
  emit(type: string, data: unknown) {
    this.listeners[type](new MessageEvent(type, { data: JSON.stringify(data) }))
  }
}

beforeEach(() => vi.stubGlobal('EventSource', FakeEventSource))
afterEach(() => vi.unstubAllGlobals())

function handlers() {
  return { streams: vi.fn(), error: vi.fn(), open: vi.fn(), lost: vi.fn() }
}

test('подключается к live-потоку кампании и разбирает события', () => {
  const on = handlers()

  openLiveConnection(217109, on)
  const source = FakeEventSource.last
  source.onopen!()
  source.emit('streams', [{ id: 1 }])
  source.emit('keitaro_error', { detail: 'Keitaro API error (401): Invalid API key' })
  source.onerror!()

  expect(source.url).toBe('/api/campaigns/217109/live')
  expect(on.open).toHaveBeenCalled()
  expect(on.streams).toHaveBeenCalledWith([{ id: 1 }])
  expect(on.error).toHaveBeenCalledWith('Keitaro API error (401): Invalid API key')
  expect(on.lost).toHaveBeenCalled()
})

test('закрытие соединения', () => {
  const close = openLiveConnection(217109, handlers())

  close()

  expect(FakeEventSource.last.closed).toBe(true)
})
