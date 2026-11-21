import { OFFERS, offer, stream } from '@/test/streams'

import { streamSummary } from './streamSummary'

test('сумма — только по активным офферам; при 100% предупреждений нет', () => {
  const s = stream(1, [offer(1, 50), offer(2, 0, { status: 'removed' }), offer(3, 50)])

  expect(streamSummary(s)).toMatchObject({ total: 100, warnings: [] })
})

test('сумма активных долей не 100% — постоянное предупреждение потока', () => {
  const s = stream(1, [offer(1, 20, { pinned: true })])

  expect(streamSummary(s).warnings).toEqual(['Сумма долей 20%, а не 100%: Keitaro распределит трафик по этим долям как есть'])
})

test('поток без активных офферов не предупреждает о сумме', () => {
  expect(streamSummary(stream(1, [offer(1, 0, { status: 'removed' })])).warnings).toEqual([])
  expect(streamSummary(stream(1, [])).warnings).toEqual([])
})

test('считает изменения черновика, конфликты и пометки Keitaro', () => {
  const s = stream(1, [
    offer(1, 50, { changed: true, conflict: true }),
    offer(2, 50, { changed: true }),
    offer(3, 0, { keitaro_change: 'removed' }),
  ])

  expect(streamSummary(s)).toMatchObject({ changes: 2, conflicts: 1, marks: 1 })
  expect(streamSummary(OFFERS)).toMatchObject({ changes: 0, conflicts: 0, marks: 0 })
})
