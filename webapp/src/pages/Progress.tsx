import { useQuery } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router'

import { type DayStats, getStatsSummary, getTargets } from '../api/client'
import ChoiceGroup from '../components/ChoiceGroup'
import TrendChart from '../components/TrendChart'
import { useBackButton } from '../hooks/useBackButton'
import { fmtSleep } from '../lib/checkin'

type Period = '7' | '30' | '90'

const PERIODS: { value: Period; label: string }[] = [
  { value: '7', label: 'Неделя' },
  { value: '30', label: 'Месяц' },
  { value: '90', label: '3 месяца' },
]

const num = (v: number, digits = 0) =>
  v.toLocaleString('ru', { maximumFractionDigits: digits, minimumFractionDigits: 0 })

function average(values: (number | null)[]): number | null {
  const present = values.filter((v): v is number => v !== null)
  return present.length ? present.reduce((a, b) => a + b, 0) / present.length : null
}

// 1 тренировка, 2 тренировки, 5 тренировок
function workoutsWord(n: number): string {
  const tens = n % 100
  const ones = n % 10
  if (ones === 1 && tens !== 11) return 'тренировка'
  if (ones >= 2 && ones <= 4 && (tens < 12 || tens > 14)) return 'тренировки'
  return 'тренировок'
}

const column = <K extends keyof DayStats>(days: DayStats[], key: K) => days.map((d) => d[key])

export default function Progress() {
  const navigate = useNavigate()
  useBackButton(useCallback(() => navigate('/'), [navigate]))
  const [period, setPeriod] = useState<Period>('30')
  const summary = useQuery({
    queryKey: ['stats', period],
    queryFn: () => getStatsSummary(Number(period)),
  })
  const targets = useQuery({ queryKey: ['targets'], queryFn: getTargets })

  const days = summary.data ?? []
  const dates = days.map((d) => d.date)

  const weight = column(days, 'weight_kg')
  const weights = weight.filter((v): v is number => v !== null)
  // Последний вес и изменение с начала периода
  let weightSummary = ''
  if (weights.length) {
    const last = weights[weights.length - 1]
    const delta = last - weights[0]
    const sign = delta > 0 ? '+' : delta < 0 ? '−' : '±'
    weightSummary = `${num(last, 1)} кг`
    if (weights.length > 1) weightSummary += ` (${sign}${num(Math.abs(delta), 1)})`
  }

  const kcal = column(days, 'kcal')
  const sleep = days.map((d) => (d.sleep_minutes === null ? null : d.sleep_minutes / 60))
  const volume = days.map((d) => (d.workouts > 0 ? d.volume_kg : null))
  const workoutCount = days.reduce((sum, d) => sum + d.workouts, 0)

  const avgText = (values: (number | null)[], fmt: (v: number) => string) => {
    const avg = average(values)
    return avg === null ? '' : `в среднем ${fmt(avg)}`
  }
  const fmtScore = (v: number) => `${num(v, 1)} из 5`
  const fmtHours = (v: number) => fmtSleep(Math.round(v * 60))

  const scores: { key: 'energy' | 'mood' | 'stress' | 'sleep_quality'; title: string }[] = [
    { key: 'sleep_quality', title: 'Качество сна' },
    { key: 'energy', title: 'Энергия' },
    { key: 'mood', title: 'Настроение' },
    { key: 'stress', title: 'Стресс' },
  ]

  return (
    <main className="p-4">
      <h1 className="text-xl font-semibold">Прогресс</h1>
      <div className="mt-4">
        <ChoiceGroup options={PERIODS} value={period} onChange={setPeriod} columns={3} />
      </div>

      {summary.isPending && <p className="mt-4 text-hint">Загружаю…</p>}
      {summary.isError && (
        <p className="mt-4 text-hint">Не удалось загрузить данные. Попробуйте ещё раз.</p>
      )}

      {summary.data && (
        <div className="mt-4 flex flex-col gap-3">
          <TrendChart
            title="Вес"
            dates={dates}
            values={weight}
            kind="line"
            format={(v) => `${num(v, 1)} кг`}
            summary={weightSummary}
          />
          <TrendChart
            title="Калории"
            dates={dates}
            values={kcal}
            kind="bar"
            format={(v) => `${num(v)} ккал`}
            summary={avgText(kcal, (v) => `${num(v)} ккал`)}
            reference={
              targets.data
                ? { value: targets.data.kcal, label: `норма ${num(targets.data.kcal)}` }
                : undefined
            }
          />
          <TrendChart
            title="Сон"
            dates={dates}
            values={sleep}
            kind="bar"
            format={fmtHours}
            summary={avgText(sleep, fmtHours)}
          />
          {scores.map((s) => {
            const values = column(days, s.key)
            return (
              <TrendChart
                key={s.key}
                title={s.title}
                dates={dates}
                values={values}
                kind="line"
                domain={[1, 5]}
                format={fmtScore}
                summary={avgText(values, fmtScore)}
              />
            )
          })}
          <TrendChart
            title="Объём тренировок"
            dates={dates}
            values={volume}
            kind="bar"
            format={(v) => `${num(v)} кг`}
            summary={workoutCount ? `${workoutCount} ${workoutsWord(workoutCount)}` : ''}
          />
          <p className="text-xs text-hint">
            Нажмите на график, чтобы увидеть значение за день. Объём — повторы × вес по выполненным
            подходам.
          </p>
        </div>
      )}
    </main>
  )
}
