import { useQuery } from '@tanstack/react-query'
import type { CSSProperties } from 'react'
import { Link, Navigate } from 'react-router'

import {
  ApiError,
  getCheckins,
  getDiary,
  getMe,
  getStreak,
  getTargets,
  getWater,
} from '../api/client'
import DayRings from '../components/DayRings'
import StreakCard from '../components/StreakCard'
import { fmtSleep } from '../lib/checkin'
import { fmtGrams, todayIn } from '../lib/nutrition'
import { isInTelegram } from '../lib/telegram'

// Цель сна для кольца — 8 часов
const SLEEP_GOAL_MIN = 8 * 60

const SECTIONS: { emoji: string; title: string; hint: string; to: string; hue: string }[] = [
  { emoji: '🍽', title: 'Питание', hint: 'Дневник, КБЖУ, вода', to: '/nutrition', hue: 'var(--hue-food)' },
  { emoji: '🏋️', title: 'Тренировки', hint: 'Подходы, RPE, план', to: '/workouts', hue: 'var(--hue-train)' },
  { emoji: '😴', title: 'Сон и самочувствие', hint: 'Чек-ин дня', to: '/checkin', hue: 'var(--hue-sleep)' },
  { emoji: '⚖️', title: 'Вес', hint: 'Журнал и график', to: '/weight', hue: 'var(--hue-water)' },
]

const fmtInt = (v: number) => Math.round(v).toLocaleString('ru-RU')
const fmtLiters = (ml: number) => (ml / 1000).toFixed(1).replace('.', ',').replace(',0', '')

function Legend(props: { to: string; color: string; label: string; value: string; of?: string }) {
  return (
    <li>
      <Link to={props.to} className="block">
        <div className="flex items-center gap-1.5 text-xs text-hint">
          <span className="size-2 rounded-full" style={{ background: props.color }} />
          {props.label}
        </div>
        <div className="font-display mt-0.5 truncate text-lg leading-tight font-bold tabular-nums">
          {props.value}
          {props.of && <span className="text-sm font-medium text-hint"> {props.of}</span>}
        </div>
      </Link>
    </li>
  )
}

export default function Home() {
  const me = useQuery({ queryKey: ['me'], queryFn: getMe, enabled: isInTelegram })
  const onboarded = Boolean(me.data?.onboarded_at)
  const today = todayIn(me.data?.timezone)
  const targets = useQuery({ queryKey: ['targets'], queryFn: getTargets, enabled: onboarded })
  // Записи делают на других экранах — при возврате на главную пересчитываем всё за сегодня
  const fresh = { enabled: onboarded, refetchOnMount: 'always' as const }
  const streak = useQuery({ queryKey: ['streak'], queryFn: getStreak, ...fresh })
  const diary = useQuery({ queryKey: ['diary', today], queryFn: () => getDiary(today), ...fresh })
  const water = useQuery({ queryKey: ['water', today], queryFn: () => getWater(today), ...fresh })
  const checkins = useQuery({
    queryKey: ['checkins', today, today],
    queryFn: () => getCheckins(today, today),
    ...fresh,
  })

  if (!isInTelegram) {
    return (
      <main className="p-4">
        <h1 className="page-title">FitTrack</h1>
        <p className="mt-2 text-hint">Откройте приложение через бота в Telegram.</p>
      </main>
    )
  }

  if (me.data && !onboarded) return <Navigate to="/onboarding" replace />

  const eaten = diary.data?.total
  const kcalTarget = targets.data?.kcal ?? 0
  const sleep = checkins.data?.[0]?.sleep_minutes ?? null
  const dateLabel = new Date(`${today}T00:00:00Z`).toLocaleDateString('ru-RU', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    timeZone: 'UTC',
  })

  const macros = targets.data
    ? [
        { label: 'Белки', value: eaten?.protein ?? 0, target: targets.data.protein_g },
        { label: 'Жиры', value: eaten?.fat ?? 0, target: targets.data.fat_g },
        { label: 'Углеводы', value: eaten?.carbs ?? 0, target: targets.data.carbs_g },
      ]
    : []

  return (
    <main className="p-4 pb-10">
      <header>
        <p className="text-sm text-hint first-letter:uppercase">{dateLabel}</p>
        <h1 className="page-title mt-0.5">
          {me.data ? `Привет, ${me.data.first_name}!` : 'FitTrack'}
        </h1>
      </header>

      {me.isError && (
        <p className="mt-2 text-hint">
          {/* initData действует 24 часа — после этого нужен новый запуск из бота */}
          {me.error instanceof ApiError && me.error.status === 401
            ? 'Сессия устарела. Закройте приложение и откройте его снова из бота.'
            : 'Не удалось загрузить профиль. Проверьте интернет и попробуйте ещё раз.'}
        </p>
      )}

      {onboarded && (
        <section className="card mt-5 rounded-3xl p-4" aria-label="Сегодня">
          <div className="flex items-center gap-4">
            <DayRings
              rings={[
                {
                  label: 'Еда',
                  color: 'var(--hue-food)',
                  value: kcalTarget ? (eaten?.kcal ?? 0) / kcalTarget : 0,
                },
                {
                  label: 'Вода',
                  color: 'var(--hue-water)',
                  value: water.data ? water.data.ml / water.data.target_ml : 0,
                },
                { label: 'Сон', color: 'var(--hue-sleep)', value: (sleep ?? 0) / SLEEP_GOAL_MIN },
              ]}
            />
            <ul className="min-w-0 flex-1 space-y-2.5">
              <Legend
                to="/nutrition"
                color="var(--hue-food)"
                label="Еда"
                value={eaten ? fmtInt(eaten.kcal) : '—'}
                of={kcalTarget ? `/ ${fmtInt(kcalTarget)} ккал` : 'ккал'}
              />
              <Legend
                to="/nutrition"
                color="var(--hue-water)"
                label="Вода"
                value={water.data ? fmtLiters(water.data.ml) : '—'}
                of={water.data ? `/ ${fmtLiters(water.data.target_ml)} л` : 'л'}
              />
              <Legend
                to="/checkin"
                color="var(--hue-sleep)"
                label="Сон"
                value={sleep !== null ? fmtSleep(sleep) : 'Отметить'}
              />
            </ul>
          </div>

          {macros.length > 0 && (
            <div className="mt-4 grid grid-cols-3 gap-3">
              {macros.map((m) => (
                <div key={m.label}>
                  <div className="flex items-baseline justify-between text-xs text-hint">
                    <span>{m.label}</span>
                    <span className="tabular-nums">
                      {fmtGrams(m.value)}/{m.target}
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-[color-mix(in_oklab,var(--hue-food)_16%,transparent)]">
                    <div
                      className="h-full rounded-full bg-food"
                      style={{ width: `${Math.min(100, (m.value / (m.target || 1)) * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {streak.data && (
        <div className="mt-4">
          <StreakCard streak={streak.data} />
        </div>
      )}

      <ul className="mt-4 grid grid-cols-2 gap-3">
        {SECTIONS.map((s) => (
          <li key={s.to} className="rounded-2xl bg-bg-secondary">
            <Link to={s.to} className="block p-4">
              <Tile emoji={s.emoji} hue={s.hue} />
              <div className="mt-3 font-semibold">{s.title}</div>
              <div className="text-sm text-hint">{s.hint}</div>
            </Link>
          </li>
        ))}
        <li className="col-span-2 rounded-2xl bg-bg-secondary">
          <Link to="/stats" className="flex items-center gap-3 p-4">
            <Tile emoji="📈" hue="var(--accent)" />
            <div className="min-w-0 flex-1">
              <div className="font-semibold">Прогресс</div>
              <div className="text-sm text-hint">Графики, рекорды и достижения</div>
            </div>
            <span className="text-xl text-hint" aria-hidden>
              ›
            </span>
          </Link>
        </li>
      </ul>

      {targets.data && (
        <Link to="/onboarding" className="mt-4 inline-block text-sm text-link">
          Профиль и цели
        </Link>
      )}

      <p className="mt-6 text-xs text-hint">
        Приложение носит информационный характер и не заменяет консультацию врача, диетолога или
        тренера.
      </p>
    </main>
  )
}

/** Иконка раздела: эмодзи на плашке в цвет раздела. */
function Tile({ emoji, hue }: { emoji: string; hue: string }) {
  const style: CSSProperties = {
    background: `linear-gradient(140deg, color-mix(in oklab, ${hue} 92%, white), color-mix(in oklab, ${hue} 70%, black))`,
    boxShadow: `0 8px 18px -10px ${hue}`,
  }
  return (
    <span className="grid size-11 shrink-0 place-items-center rounded-[14px] text-2xl" style={style}>
      {emoji}
    </span>
  )
}
