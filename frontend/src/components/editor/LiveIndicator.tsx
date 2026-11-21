import { useUnit } from 'effector-react'

import { cn } from '@/lib/utils'
import { $liveError, $liveStatus } from '@/models/editor'

const LABEL = { off: '', connecting: 'Подключение…', live: 'Live', lost: 'Нет связи, переподключаемся…' }

/** Компактное состояние live-обновления; подробности ошибки Keitaro — в плашке над потоками. */
export function LiveIndicator() {
  const [status, error] = useUnit([$liveStatus, $liveError])
  if (status === 'off') return null

  const ok = status === 'live' && error === null
  return (
    <span
      className={cn(
        'flex items-center gap-1.5 text-sm',
        ok ? 'text-emerald-700 dark:text-emerald-400' : 'text-muted-foreground',
        error && 'text-amber-700 dark:text-amber-400',
      )}
      title={ok ? 'Изменения в Keitaro появляются автоматически' : undefined}
    >
      <span aria-hidden className={cn('size-2 rounded-full bg-current', ok && 'animate-pulse')} />
      {error ? 'Keitaro не отвечает' : LABEL[status]}
    </span>
  )
}
