import { AlertTriangle, Info, XCircle } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

const TONE = {
  error: { icon: XCircle, className: 'border-destructive/30 bg-destructive/5 text-destructive' },
  warning: { icon: AlertTriangle, className: 'border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200' },
  info: { icon: Info, className: 'border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-900 dark:bg-sky-950/40 dark:text-sky-200' },
}

type Props = {
  tone: keyof typeof TONE
  children: ReactNode
  /** Кнопки справа: «Закрыть», «Всё моё» и т.п. */
  actions?: ReactNode
  role?: 'alert' | 'status'
  className?: string
}

/** Сообщение внутри потока или над потоками: ошибка, предупреждение или пояснение. */
export function Notice({ tone, children, actions, role, className }: Props) {
  const { icon: Icon, className: toneClass } = TONE[tone]
  return (
    <div role={role} className={cn('flex flex-wrap items-start gap-x-3 gap-y-2 rounded-lg border px-3 py-2 text-sm', toneClass, className)}>
      <Icon aria-hidden className="mt-0.5 size-4 shrink-0" />
      <div className="min-w-48 flex-1">{children}</div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}
