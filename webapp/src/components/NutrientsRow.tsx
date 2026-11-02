import type { Nutrients } from '../api/client'
import { fmtGrams, fmtKcal } from '../lib/nutrition'

/** КБЖУ порции четырьмя плитками. */
export default function NutrientsRow({ n }: { n: Nutrients }) {
  const cells = [
    { label: 'ккал', value: fmtKcal(n.kcal) },
    { label: 'белки', value: fmtGrams(n.protein) },
    { label: 'жиры', value: fmtGrams(n.fat) },
    { label: 'углев.', value: fmtGrams(n.carbs) },
  ]
  return (
    <div className="grid grid-cols-4 gap-2 text-center">
      {cells.map((c) => (
        <div key={c.label} className="rounded-xl bg-bg-secondary py-2">
          <div className="text-lg font-semibold">{c.value}</div>
          <div className="text-xs text-hint">{c.label}</div>
        </div>
      ))}
    </div>
  )
}
