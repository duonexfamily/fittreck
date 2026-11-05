import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router'

import {
  ApiError,
  type WeightEntry,
  deleteWeight,
  getMe,
  getWeightHistory,
  putWeight,
} from '../api/client'
import SliderField from '../components/SliderField'
import { useBackButton } from '../hooks/useBackButton'
import { useMainButton } from '../hooks/useMainButton'
import { fmtGrams, formatDay, todayIn } from '../lib/nutrition'
import { haptic } from '../lib/telegram'

const fmtKg = fmtGrams

/** Мини-график веса: линия по дням, ось X — реальные даты, а не номера записей. */
function WeightChart({ entries }: { entries: WeightEntry[] }) {
  const W = 300
  const H = 100
  const PAD = 6
  const days = entries.map((e) => new Date(`${e.date}T00:00:00Z`).getTime())
  const weights = entries.map((e) => e.weight_kg)
  const [d0, d1] = [days[0], days[days.length - 1]]
  const [min, max] = [Math.min(...weights), Math.max(...weights)]
  // Ровная линия при одинаковом весе — посередине
  const span = max - min || 1
  const x = (d: number) => PAD + ((d - d0) / (d1 - d0 || 1)) * (W - 2 * PAD)
  const y = (w: number) => (max === min ? H / 2 : PAD + ((max - w) / span) * (H - 2 * PAD))
  const points = entries.map((_, i) => `${x(days[i])},${y(weights[i])}`).join(' ')

  return (
    <section className="rounded-2xl bg-bg-secondary p-4">
      <div className="flex justify-between text-xs text-hint">
        <span>Последние 90 дней</span>
        <span>
          {fmtKg(min)}–{fmtKg(max)} кг
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 h-28 w-full" preserveAspectRatio="none">
        <polyline
          points={points}
          fill="none"
          stroke="var(--tg-theme-button-color, #2481cc)"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </section>
  )
}

export default function Weight() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const me = useQuery({ queryKey: ['me'], queryFn: getMe })
  const history = useQuery({ queryKey: ['weight'], queryFn: getWeightHistory })
  const today = todayIn(me.data?.timezone)

  const entries = history.data ?? []
  const last = entries.at(-1)
  const todayEntry = last?.date === today ? last : undefined
  // Пока пользователь не двигал слайдер — показываем последний вес
  const [touched, setTouched] = useState<number | null>(null)
  const weight = touched ?? last?.weight_kg ?? 70

  useBackButton(useCallback(() => navigate('/'), [navigate]))

  const onDone = async () => {
    haptic.success()
    // Норма КБЖУ и воды считаются от последнего веса
    await Promise.all(
      ['weight', 'targets', 'water'].map((key) =>
        queryClient.invalidateQueries({ queryKey: [key] }),
      ),
    )
  }
  const save = useMutation({
    mutationFn: () => putWeight({ date: today, weight_kg: Math.round(weight * 10) / 10 }),
    onSuccess: async () => {
      await onDone()
      setTouched(null)
    },
    onError: () => haptic.error(),
  })
  const remove = useMutation({
    mutationFn: deleteWeight,
    onSuccess: onDone,
    onError: () => haptic.error(),
  })

  const valid = me.isSuccess && weight >= 30 && weight <= 300 && weight !== todayEntry?.weight_kg
  const submit = useCallback(() => {
    if (valid && !save.isPending) save.mutate()
  }, [valid, save])
  useMainButton({
    text: todayEntry ? 'Обновить вес за сегодня' : 'Записать вес',
    onClick: submit,
    enabled: valid,
    loading: save.isPending,
  })

  const recent = entries.slice(-14).reverse()

  return (
    <main className="p-4 pb-10">
      <h1 className="page-title">Вес</h1>

      <div className="mt-4">
        <SliderField
          label={todayEntry ? 'Сегодня' : 'Вес сегодня'}
          unit="кг"
          value={weight}
          min={30}
          max={200}
          step={0.1}
          onChange={setTouched}
        />
      </div>
      <p className="mt-2 text-sm text-hint">
        Взвешивайтесь утром натощак — так цифры проще сравнивать.
      </p>

      {history.isError && <p className="mt-4 text-hint">Не удалось загрузить историю.</p>}
      {entries.length >= 2 && (
        <div className="mt-4">
          <WeightChart entries={entries} />
        </div>
      )}

      {recent.length > 0 && (
        <section className="mt-4 rounded-2xl bg-bg-secondary px-4 py-2">
          <ul className="divide-y divide-bg">
            {recent.map((e, i) => {
              const prev = recent[i + 1]
              const diff = prev ? Math.round((e.weight_kg - prev.weight_kg) * 10) / 10 : 0
              return (
                <li key={e.date} className="flex items-center justify-between gap-3 py-2">
                  <span className="text-sm text-hint">{formatDay(e.date, today)}</span>
                  <span className="ml-auto">
                    {fmtKg(e.weight_kg)} кг
                    {diff !== 0 && (
                      <span className="ml-2 text-xs text-hint">
                        {diff > 0 ? '+' : '−'}
                        {fmtKg(Math.abs(diff))}
                      </span>
                    )}
                  </span>
                  <button
                    type="button"
                    disabled={remove.isPending || entries.length <= 1}
                    onClick={() => remove.mutate(e.date)}
                    className="px-2 text-hint disabled:invisible"
                    aria-label={`Удалить запись за ${formatDay(e.date, today)}`}
                  >
                    ×
                  </button>
                </li>
              )
            })}
          </ul>
        </section>
      )}

      {(save.isError || remove.isError) && (
        <p className="mt-4 text-sm text-destructive">
          {remove.error instanceof ApiError && remove.error.status === 409
            ? 'Нужна хотя бы одна запись веса — по ней считается норма.'
            : 'Не получилось. Попробуйте ещё раз.'}
        </p>
      )}

      <p className="mt-6 text-xs text-hint">
        Вес колеблется день ото дня — смотрите на тенденцию за несколько недель. Приложение носит
        информационный характер и не заменяет консультацию врача.
      </p>
    </main>
  )
}
