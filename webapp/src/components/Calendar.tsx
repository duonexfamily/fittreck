import { haptic } from '../lib/telegram'

/** Отметка дня: выполненная тренировка, незавершённая или запланированная, или обе сразу. */
export interface DayMark {
  done: boolean
  planned: boolean
}

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

/** Первый и последний день месяца YYYY-MM. */
export function monthRange(month: string): { from: string; to: string } {
  const [y, m] = month.split('-').map(Number)
  const last = new Date(Date.UTC(y, m, 0)).getUTCDate()
  return { from: `${month}-01`, to: `${month}-${String(last).padStart(2, '0')}` }
}

export function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1 + delta, 1)).toISOString().slice(0, 7)
}

/** Ячейки сетки с понедельника: null — пустые клетки до первого числа. */
function monthCells(month: string): (string | null)[] {
  const { from, to } = monthRange(month)
  // getUTCDay: 0 — воскресенье; сдвигаем, чтобы неделя начиналась с понедельника
  const lead = (new Date(`${from}T00:00:00Z`).getUTCDay() + 6) % 7
  const days = Number(to.slice(8))
  return [
    ...Array<null>(lead).fill(null),
    ...Array.from({ length: days }, (_, i) => `${month}-${String(i + 1).padStart(2, '0')}`),
  ]
}

function monthTitle(month: string): string {
  const title = new Date(`${month}-01T00:00:00Z`).toLocaleDateString('ru-RU', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })
  return title.charAt(0).toUpperCase() + title.slice(1).replace(/\s*г\.$/, '')
}

export default function Calendar({
  month,
  today,
  selected,
  marks,
  onSelect,
  onMonth,
}: {
  month: string
  today: string
  selected: string
  marks: Record<string, DayMark>
  onSelect: (date: string) => void
  onMonth: (month: string) => void
}) {
  const flip = (delta: number) => {
    haptic.select()
    onMonth(shiftMonth(month, delta))
  }
  return (
    <section className="rounded-2xl bg-bg-secondary p-3">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => flip(-1)}
          className="px-3 py-1 text-lg text-link"
          aria-label="Предыдущий месяц"
        >
          ‹
        </button>
        <h2 className="font-medium">{monthTitle(month)}</h2>
        <button
          type="button"
          onClick={() => flip(1)}
          className="px-3 py-1 text-lg text-link"
          aria-label="Следующий месяц"
        >
          ›
        </button>
      </div>
      <div className="mt-2 grid grid-cols-7 text-center text-xs text-hint">
        {WEEKDAYS.map((d) => (
          <div key={d}>{d}</div>
        ))}
      </div>
      <div className="mt-1 grid grid-cols-7 gap-y-1 text-center">
        {monthCells(month).map((date, i) => {
          if (date === null) return <div key={`empty-${i}`} />
          const mark = marks[date]
          const isSelected = date === selected
          const cell = isSelected
            ? 'bg-button text-button-text'
            : date === today
              ? 'font-semibold text-link'
              : ''
          return (
            <button
              key={date}
              type="button"
              onClick={() => {
                haptic.select()
                onSelect(date)
              }}
              className={`mx-auto flex size-10 flex-col items-center justify-center rounded-full ${cell}`}
              aria-label={date}
              aria-pressed={isSelected}
            >
              <span className="text-sm leading-none">{Number(date.slice(8))}</span>
              <span className="mt-1 flex h-1.5 gap-0.5">
                {mark?.done && (
                  <span
                    className={`size-1.5 rounded-full ${isSelected ? 'bg-button-text' : 'bg-button'}`}
                  />
                )}
                {mark?.planned && (
                  <span
                    className={`size-1.5 rounded-full border ${isSelected ? 'border-button-text' : 'border-link'}`}
                  />
                )}
              </span>
            </button>
          )
        })}
      </div>
      <div className="mt-2 flex justify-center gap-4 text-xs text-hint">
        <span className="flex items-center gap-1">
          <span className="size-1.5 rounded-full bg-button" /> выполнена
        </span>
        <span className="flex items-center gap-1">
          <span className="size-1.5 rounded-full border border-link" /> в плане
        </span>
      </div>
    </section>
  )
}
