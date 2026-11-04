import { useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useRef } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'

import {
  type Meal,
  type MealItem,
  type Nutrients,
  getDiary,
  getMe,
  getTargets,
} from '../api/client'
import WaterCard from '../components/WaterCard'
import { useBackButton } from '../hooks/useBackButton'
import {
  MEAL_LABELS,
  fmtGrams,
  fmtKcal,
  formatDay,
  isMealType,
  shiftDate,
  todayIn,
} from '../lib/nutrition'
import { haptic } from '../lib/telegram'

function Progress({ value, target }: { value: number; target: number }) {
  const pct = target > 0 ? Math.min(100, (value / target) * 100) : 0
  return (
    <div className="h-1.5 overflow-hidden rounded-full bg-bg">
      <div
        className={`h-full rounded-full ${value > target ? 'bg-red-500' : 'bg-button'}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

function DaySummary({ total, target }: { total: Nutrients; target?: Nutrients }) {
  const macros = [
    { label: 'Белки', value: total.protein, target: target?.protein },
    { label: 'Жиры', value: total.fat, target: target?.fat },
    { label: 'Углеводы', value: total.carbs, target: target?.carbs },
  ]
  const left = target ? Math.round(target.kcal - total.kcal) : null
  return (
    <section className="rounded-2xl bg-bg-secondary p-4">
      <div className="flex items-baseline justify-between">
        <div className="text-3xl font-semibold">
          {fmtKcal(total.kcal)}
          {target && <span className="text-base font-normal text-hint"> / {target.kcal} ккал</span>}
        </div>
        {left !== null && (
          <div className="text-sm text-hint">
            {left >= 0 ? `осталось ${left}` : `сверх нормы ${-left}`}
          </div>
        )}
      </div>
      {target && (
        <div className="mt-2">
          <Progress value={total.kcal} target={target.kcal} />
        </div>
      )}
      <div className="mt-4 grid grid-cols-3 gap-3">
        {macros.map((m) => (
          <div key={m.label}>
            <div className="text-xs text-hint">{m.label}</div>
            <div className="mt-0.5 text-sm font-medium">
              {fmtGrams(m.value)}
              {m.target !== undefined && <span className="text-hint"> / {m.target}</span>} г
            </div>
            {m.target !== undefined && (
              <div className="mt-1">
                <Progress value={m.value} target={m.target} />
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}

function MealCard({
  meal,
  date,
  highlighted,
  onItemClick,
}: {
  meal: Meal
  date: string
  highlighted: boolean
  onItemClick: (item: MealItem) => void
}) {
  const ref = useRef<HTMLElement>(null)
  useEffect(() => {
    if (highlighted) ref.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [highlighted])

  return (
    <section
      ref={ref}
      className={`rounded-2xl bg-bg-secondary p-4 ${highlighted ? 'ring-2 ring-button' : ''}`}
    >
      <div className="flex items-baseline justify-between">
        <h2 className="font-medium">{MEAL_LABELS[meal.meal_type]}</h2>
        {meal.items.length > 0 && (
          <span className="text-sm text-hint">{fmtKcal(meal.total.kcal)} ккал</span>
        )}
      </div>
      {meal.items.length > 0 && (
        <ul className="mt-2 divide-y divide-bg">
          {meal.items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onItemClick(item)}
                className="flex w-full items-baseline justify-between gap-3 py-2 text-left"
              >
                <span className="min-w-0">
                  <span className="block truncate">{item.name}</span>
                  <span className="text-xs text-hint">
                    {item.grams === null ? 'быстрая запись' : `${fmtGrams(item.grams)} г`}
                  </span>
                </span>
                <span className="shrink-0 text-sm">{fmtKcal(item.kcal)} ккал</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <Link
        to={`/nutrition/add?meal=${meal.meal_type}&date=${date}`}
        className="mt-2 inline-block text-sm font-medium text-link"
      >
        + Добавить
      </Link>
    </section>
  )
}

export default function Nutrition() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const me = useQuery({ queryKey: ['me'], queryFn: getMe })
  const targets = useQuery({ queryKey: ['targets'], queryFn: getTargets })

  const today = todayIn(me.data?.timezone)
  const date = params.get('date') ?? today
  const highlight = params.get('meal')

  const diary = useQuery({
    queryKey: ['diary', date],
    queryFn: () => getDiary(date),
    enabled: me.isSuccess,
  })

  useBackButton(useCallback(() => navigate('/'), [navigate]))

  const goTo = (days: number) => {
    haptic.select()
    // При смене дня подсветка приёма пищи из напоминания больше не нужна
    setParams({ date: shiftDate(date, days) }, { replace: true })
  }

  const target = targets.data && {
    kcal: targets.data.kcal,
    protein: targets.data.protein_g,
    fat: targets.data.fat_g,
    carbs: targets.data.carbs_g,
  }

  return (
    <main className="p-4 pb-10">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => goTo(-1)}
          className="rounded-full px-3 py-1 text-2xl text-link"
          aria-label="Предыдущий день"
        >
          ‹
        </button>
        <h1 className="text-lg font-semibold">{formatDay(date, today)}</h1>
        <button
          type="button"
          onClick={() => goTo(1)}
          disabled={date >= today}
          className="rounded-full px-3 py-1 text-2xl text-link disabled:invisible"
          aria-label="Следующий день"
        >
          ›
        </button>
      </div>

      {diary.isError && <p className="mt-4 text-hint">Не удалось загрузить дневник.</p>}
      {diary.isPending && <p className="mt-4 text-hint">Загрузка…</p>}

      {diary.data && (
        <div className="mt-3 grid gap-3">
          <DaySummary total={diary.data.total} target={target} />
          <WaterCard date={date} />
          {diary.data.meals.map((meal) => (
            <MealCard
              key={meal.meal_type}
              meal={meal}
              date={date}
              highlighted={isMealType(highlight) && highlight === meal.meal_type}
              onItemClick={(item) =>
                navigate(`/nutrition/item/${item.id}?date=${date}`, { state: { item } })
              }
            />
          ))}
        </div>
      )}

      <p className="mt-6 text-xs text-hint">
        КБЖУ продуктов — усреднённые табличные значения. Приложение носит информационный характер и
        не заменяет консультацию врача или диетолога.
      </p>
    </main>
  )
}
