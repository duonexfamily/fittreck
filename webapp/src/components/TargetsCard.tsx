import type { Targets } from '../api/client'

export default function TargetsCard({ targets }: { targets: Targets }) {
  const macros = [
    { label: 'Белки', value: targets.protein_g },
    { label: 'Жиры', value: targets.fat_g },
    { label: 'Углеводы', value: targets.carbs_g },
  ]
  return (
    <section className="rounded-2xl bg-bg-secondary p-4">
      <div className="text-sm text-hint">Ваша норма в день</div>
      <div className="mt-1 text-3xl font-semibold">
        {targets.kcal} <span className="text-base font-normal text-hint">ккал</span>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
        {macros.map((m) => (
          <div key={m.label} className="rounded-xl bg-bg py-2">
            <div className="text-lg font-semibold">{m.value} г</div>
            <div className="text-xs text-hint">{m.label}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
