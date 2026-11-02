import { haptic } from '../lib/telegram'

interface Option<T extends string> {
  value: T
  label: string
  hint?: string
}

interface Props<T extends string> {
  options: Option<T>[]
  value: T | null
  onChange: (value: T) => void
  columns?: 1 | 2 | 3
}

/** Выбор одного варианта крупными кнопками — удобнее выпадающих списков на телефоне. */
export default function ChoiceGroup<T extends string>({
  options,
  value,
  onChange,
  columns = 2,
}: Props<T>) {
  const grid = { 1: 'grid-cols-1', 2: 'grid-cols-2', 3: 'grid-cols-3' }[columns]
  return (
    <div className={`grid gap-2 ${grid}`} role="radiogroup">
      {options.map((o) => {
        const selected = o.value === value
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => {
              haptic.select()
              onChange(o.value)
            }}
            className={`rounded-xl px-3 py-3 text-left transition-colors ${
              selected ? 'bg-button text-button-text' : 'bg-bg-secondary'
            }`}
          >
            <div className="font-medium">{o.label}</div>
            {o.hint && (
              <div className={`text-xs ${selected ? 'opacity-80' : 'text-hint'}`}>{o.hint}</div>
            )}
          </button>
        )
      })}
    </div>
  )
}
