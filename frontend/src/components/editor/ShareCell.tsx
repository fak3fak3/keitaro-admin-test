import { useUnit } from 'effector-react'
import { Pin } from 'lucide-react'
import { useState } from 'react'

import type { StreamOffer } from '@/api/streams'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { actionRequested } from '@/models/editor'

type Props = { streamId: number; offer: StreamOffer; disabled: boolean }

/** Доля оффера: клик по проценту — ручной ввод (Enter — сохранить, Escape — отмена), рядом пин. */
export function ShareCell({ streamId, offer, disabled }: Props) {
  const act = useUnit(actionRequested)
  const [draft, setDraft] = useState<string | null>(null)
  const [invalid, setInvalid] = useState(false)
  const target = { streamId, offerId: offer.offer_id }

  if (offer.status === 'removed') return <span className="px-2.5 text-muted-foreground">{offer.share}%</span>

  function open() {
    setDraft(String(offer.share))
    setInvalid(false)
  }

  function commit() {
    const share = Number(draft)
    if (draft === '' || !Number.isInteger(share) || share < 0 || share > 100) {
      setInvalid(true) // не выбрасываем молча: поле остаётся открытым с подсказкой
      return
    }
    setDraft(null)
    if (share !== offer.share) act({ kind: 'share', ...target, share })
  }

  return (
    <div className="flex items-center gap-1">
      {draft === null ? (
        <Button variant="ghost" size="sm" className="font-semibold tabular-nums underline decoration-dotted underline-offset-4" title="Задать долю вручную" disabled={disabled} onClick={open}>
          {offer.share}%
        </Button>
      ) : (
        <div>
          <Input
            type="number"
            min={0}
            max={100}
            autoFocus
            className="h-8 w-20"
            aria-label={`Доля оффера ${offer.offer_id}, %`}
            aria-invalid={invalid}
            value={draft}
            onFocus={(event) => event.target.select()} // ввод заменяет текущее число
            onChange={(event) => {
              setDraft(event.target.value)
              setInvalid(false)
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter') commit()
              if (event.key === 'Escape') setDraft(null)
            }}
            onBlur={() => setDraft(null)}
          />
          {invalid && <p className="mt-1 text-xs text-destructive">Доля — целое число от 0 до 100</p>}
        </div>
      )}
      <Button
        variant="ghost"
        size="icon-sm"
        disabled={disabled}
        aria-label={offer.pinned ? 'Открепить долю' : 'Закрепить долю'}
        aria-pressed={offer.pinned}
        onClick={() => act({ kind: offer.pinned ? 'unpin' : 'pin', ...target })}
      >
        <Pin className={offer.pinned ? 'fill-current text-primary' : 'text-muted-foreground/50'} />
      </Button>
    </div>
  )
}
