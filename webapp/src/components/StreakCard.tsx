import type { Streak } from '../api/client'

// 1 день, 2 дня, 5 дней, 11 дней, 21 день
function daysWord(n: number): string {
  const tens = n % 100
  const ones = n % 10
  if (ones === 1 && tens !== 11) return 'день'
  if (ones >= 2 && ones <= 4 && (tens < 12 || tens > 14)) return 'дня'
  return 'дней'
}

const WEEKDAYS = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']

export default function StreakCard({ streak }: { streak: Streak }) {
  // Последняя точка — сегодня, дни недели считаем от неё назад
  const today = new Date().getDay()
  const days = streak.week.map((active, i) => ({
    active,
    label: WEEKDAYS[(today - (streak.week.length - 1 - i) + 7 * 2) % 7],
  }))

  const hint = streak.today_done
    ? 'Сегодня уже есть запись — так держать!'
    : streak.current > 0
      ? 'Сделай любую запись сегодня, чтобы не прервать серию.'
      : 'Запиши еду, воду, вес, чек-ин или тренировку — и серия начнётся.'

  return (
    <section className="rounded-2xl bg-bg-secondary p-4">
      <div className="flex items-baseline justify-between">
        <div>
          <div className="text-sm text-hint">Серия</div>
          <div className="font-display mt-1 text-3xl font-extrabold tabular-nums">
            {streak.current > 0 ? '🔥 ' : ''}
            {streak.current}{' '}
            <span className="text-base font-normal text-hint">
              {daysWord(streak.current)} подряд
            </span>
          </div>
        </div>
        {streak.best > 0 && (
          <div className="text-right text-sm text-hint">
            Рекорд
            <div className="text-base font-medium text-text">
              {streak.best} {daysWord(streak.best)}
            </div>
          </div>
        )}
      </div>
      <ol className="mt-3 grid grid-cols-7 gap-1 text-center" aria-label="Последние 7 дней">
        {days.map((d, i) => (
          <li key={i} className="flex flex-col items-center gap-1">
            <span
              className={`grid size-7 place-items-center rounded-full text-sm ${d.active ? 'streak-dot' : 'bg-bg'}`}
              aria-label={d.active ? 'есть записи' : 'нет записей'}
            />
            <span className="text-xs text-hint">{d.label}</span>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-sm text-hint">{hint}</p>
    </section>
  )
}
