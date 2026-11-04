import type { Achievement, ExerciseRecord } from '../api/client'
import { shortDate } from './TrendChart'

const num = (v: number) => v.toLocaleString('ru', { maximumFractionDigits: 1 })

export function RecordsCard({ records }: { records: ExerciseRecord[] }) {
  return (
    <section className="rounded-2xl bg-bg-secondary p-4">
      <h2 className="font-medium">Личные рекорды</h2>
      {records.length === 0 ? (
        <p className="mt-2 text-sm text-hint">
          Завершите силовую тренировку с весом — здесь появится лучший подход в каждом упражнении.
        </p>
      ) : (
        <ul className="mt-2 divide-y divide-bg">
          {records.map((r) => (
            <li key={r.exercise} className="flex items-baseline justify-between gap-3 py-2">
              <span className="min-w-0 truncate">{r.exercise}</span>
              <span className="shrink-0 text-right tabular-nums">
                <span className="font-medium">
                  {num(r.weight_kg)} кг{r.reps ? ` × ${r.reps}` : ''}
                </span>
                <span className="ml-2 text-xs text-hint">{shortDate(r.date)}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export function AchievementsCard({ achievements }: { achievements: Achievement[] }) {
  const done = achievements.filter((a) => a.achieved).length
  return (
    <section className="rounded-2xl bg-bg-secondary p-4">
      <div className="flex items-baseline justify-between">
        <h2 className="font-medium">Достижения</h2>
        <span className="text-sm text-hint tabular-nums">
          {done} из {achievements.length}
        </span>
      </div>
      <ul className="mt-3 grid grid-cols-2 gap-2">
        {achievements.map((a) => (
          <li
            key={a.key}
            className={`rounded-xl bg-bg p-3 ${a.achieved ? '' : 'opacity-60'}`}
            aria-label={`${a.title}: ${a.achieved ? 'получено' : `${a.progress} из ${a.goal}`}`}
          >
            <div className={`text-2xl ${a.achieved ? '' : 'grayscale'}`}>{a.emoji}</div>
            <div className="mt-1 text-sm font-medium">{a.title}</div>
            {a.achieved ? (
              <div className="text-xs text-hint">Получено ✅</div>
            ) : (
              <>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-bg-secondary">
                  <div
                    className="h-full rounded-full bg-button"
                    style={{ width: `${(a.progress / a.goal) * 100}%` }}
                  />
                </div>
                <div className="mt-1 text-xs text-hint tabular-nums">
                  {a.progress} из {a.goal}
                </div>
              </>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
