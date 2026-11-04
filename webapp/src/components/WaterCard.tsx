import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { addWater, getWater } from '../api/client'
import { haptic } from '../lib/telegram'

const fmtLiters = (ml: number) => (ml / 1000).toFixed(2).replace(/\.?0+$/, '').replace('.', ',')

/** Вода за день: быстрые кнопки и прогресс к ориентиру. */
export default function WaterCard({ date }: { date: string }) {
  const queryClient = useQueryClient()
  const water = useQuery({ queryKey: ['water', date], queryFn: () => getWater(date) })
  const add = useMutation({
    mutationFn: (delta: number) => addWater({ date, delta_ml: delta }),
    onSuccess: (data) => {
      haptic.success()
      queryClient.setQueryData(['water', date], data)
    },
    onError: () => haptic.error(),
  })

  if (!water.data) return null
  const { ml, target_ml } = water.data
  const pct = Math.min(100, (ml / target_ml) * 100)

  return (
    <section className="rounded-2xl bg-bg-secondary p-4">
      <div className="flex items-baseline justify-between">
        <h2 className="font-medium">💧 Вода</h2>
        <div className="text-sm">
          <span className="font-medium">{fmtLiters(ml)}</span>
          <span className="text-hint"> / {fmtLiters(target_ml)} л</span>
        </div>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-bg">
        <div className="h-full rounded-full bg-button" style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-3 flex gap-2">
        {[250, 500].map((delta) => (
          <button
            key={delta}
            type="button"
            disabled={add.isPending}
            onClick={() => add.mutate(delta)}
            className="flex-1 rounded-xl bg-bg py-2 font-medium text-link disabled:opacity-50"
          >
            +{delta} мл
          </button>
        ))}
        <button
          type="button"
          disabled={add.isPending || ml === 0}
          onClick={() => add.mutate(-250)}
          className="rounded-xl bg-bg px-3 py-2 text-hint disabled:opacity-50"
          aria-label="Убрать 250 мл"
        >
          −250
        </button>
      </div>
      {add.isError && (
        <p className="mt-2 text-sm text-destructive">Не получилось. Попробуйте ещё раз.</p>
      )}
    </section>
  )
}
