import { useUnit } from 'effector-react'

import type { Stream } from '@/api/streams'
import { Button } from '@/components/ui/button'
import { plural } from '@/lib/plural'
import { $streamErrors, actionRequested, streamErrorDismissed } from '@/models/editor'
import type { StreamSummary } from '@/models/streamSummary'

import { Notice } from './Notice'

const OFFERS: [string, string, string] = ['оффер', 'оффера', 'офферов']

type Props = { stream: Stream; summary: StreamSummary; disabled: boolean }

/** Всё, что относится к потоку, показывается на нём: ошибка действия, предупреждения, конфликты, пометки. */
export function StreamNotices({ stream, summary, disabled }: Props) {
  const [errors, act, dismiss] = useUnit([$streamErrors, actionRequested, streamErrorDismissed])
  const error = errors[stream.id]
  const streamId = stream.id
  const { conflicts, marks } = summary

  return (
    <>
      {error && (
        <Notice
          tone="error"
          role="alert"
          actions={<Button variant="ghost" size="xs" onClick={() => dismiss(streamId)}>Закрыть</Button>}
        >
          {error}
        </Notice>
      )}

      {summary.warnings.map((warning) => (
        <Notice key={warning} tone="warning">{warning}</Notice>
      ))}

      {conflicts > 0 && (
        <Notice
          tone="warning"
          actions={
            <>
              <Button variant="outline" size="xs" disabled={disabled} onClick={() => act({ kind: 'resolveAll', streamId, keep: 'mine' })}>
                Всё моё
              </Button>
              <Button variant="outline" size="xs" disabled={disabled} onClick={() => act({ kind: 'resolveAll', streamId, keep: 'keitaro' })}>
                Всё из Keitaro
              </Button>
            </>
          }
        >
          <p className="font-medium">
            {conflicts} {plural(conflicts, OFFERS)} {conflicts === 1 ? 'изменён' : 'изменены'} и у нас, и в Keitaro
          </p>
          <p>Выберите версию в строке оффера или для всех сразу. Push недоступен, пока не выбрана версия.</p>
        </Notice>
      )}

      {marks > 0 && (
        <Notice
          tone="info"
          actions={
            <Button variant="ghost" size="xs" disabled={disabled} onClick={() => act({ kind: 'acknowledge', streamId })}>
              Скрыть пометки
            </Button>
          }
        >
          С прошлой загрузки в Keitaro {marks === 1 ? 'изменился' : 'изменились'} {marks} {plural(marks, OFFERS)} — изменения
          отмечены в строках.
        </Notice>
      )}
    </>
  )
}
