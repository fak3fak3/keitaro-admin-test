import { useUnit } from 'effector-react'
import { useId } from 'react'

import { Input } from '@/components/ui/input'
import { offerLabel, type OfferSearch } from '@/models/offerSearch'

type Props = {
  search: OfferSearch
  label: string
  invalid?: boolean
}

/** Поле поиска оффера с выпадающим списком (ARIA combobox). Логика — в модели `createOfferSearch`. */
export function OfferAutocomplete({ search, label, invalid }: Props) {
  const [text, options, selected, pending, textChanged, offerSelected] = useUnit([
    search.$text,
    search.$options,
    search.$selected,
    search.$pending,
    search.textChanged,
    search.offerSelected,
  ])
  const listId = useId()
  const open = selected === null && text.trim() !== ''

  return (
    <div className="relative">
      <Input
        role="combobox"
        aria-label={label}
        aria-expanded={open}
        aria-controls={listId}
        aria-invalid={invalid || undefined}
        autoComplete="off"
        placeholder="Название или id оффера"
        value={text}
        onChange={(event) => textChanged(event.target.value)}
      />
      {open && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md border bg-popover p-1 text-sm shadow-md"
        >
          {options.map((offer) => (
            <li
              key={offer.id}
              role="option"
              aria-selected={false}
              className="cursor-pointer rounded-sm px-2 py-1.5 hover:bg-accent"
              onClick={() => offerSelected(offer)}
            >
              {offerLabel(offer)}
            </li>
          ))}
          {options.length === 0 && (
            <li className="px-2 py-1.5 text-muted-foreground">
              {pending ? 'Поиск…' : 'Ничего не найдено'}
            </li>
          )}
        </ul>
      )}
    </div>
  )
}
