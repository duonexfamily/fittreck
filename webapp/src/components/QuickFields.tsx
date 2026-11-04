import type { Nutrients } from '../api/client'
import { QUICK_DEFAULT_NAME } from '../lib/nutrition'
import NumberInput from './NumberInput'

export type QuickRaw = Record<keyof Nutrients, string>

/** Поля быстрой записи: название и КБЖУ порции. */
export default function QuickFields({
  name,
  onName,
  raw,
  onRaw,
}: {
  name: string
  onName: (v: string) => void
  raw: QuickRaw
  onRaw: (r: QuickRaw) => void
}) {
  const set = (key: keyof Nutrients) => (v: string) => onRaw({ ...raw, [key]: v })
  return (
    <>
      <input
        value={name}
        onChange={(e) => onName(e.target.value)}
        placeholder={QUICK_DEFAULT_NAME}
        maxLength={128}
        className="mt-4 w-full rounded-2xl bg-bg-secondary p-4 text-lg outline-none"
      />
      <div className="mt-2 grid gap-2">
        <NumberInput label="Калории, ккал" value={raw.kcal} onChange={set('kcal')} />
        <NumberInput
          label="Белки, г"
          value={raw.protein}
          onChange={set('protein')}
          placeholder="0"
        />
        <NumberInput label="Жиры, г" value={raw.fat} onChange={set('fat')} placeholder="0" />
        <NumberInput
          label="Углеводы, г"
          value={raw.carbs}
          onChange={set('carbs')}
          placeholder="0"
        />
      </div>
    </>
  )
}
