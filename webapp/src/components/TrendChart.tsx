import { useEffect, useRef, useState } from 'react'

interface Props {
  title: string
  // Даты YYYY-MM-DD и значения по дням. null — нет данных, линия прерывается
  dates: string[]
  values: (number | null)[]
  kind: 'line' | 'bar'
  format: (v: number) => string
  // Подпись, пока ни один день не выбран: среднее, последнее значение и т. п.
  summary: string
  // Фиксированная шкала, например оценки 1–5. Иначе — от данных
  domain?: [number, number]
  // Горизонтальная линия-ориентир, например норма калорий
  reference?: { value: number; label: string }
}

const H = 120
const PAD_TOP = 8
const PAD_BOTTOM = 4
const BAR_GAP = 2

export function shortDate(date: string): string {
  return new Date(`${date}T00:00:00Z`).toLocaleDateString('ru', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  })
}

/** Ширина элемента в пикселях — чтобы скругления и точки не растягивались вместе с SVG. */
function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(el)
    return () => observer.disconnect()
  }, [])
  return [ref, width] as const
}

/** Столбик со скруглённым верхом, низ — ровно на базовой линии. */
function barPath(x: number, y: number, w: number, base: number): string {
  const r = Math.min(4, w / 2, base - y)
  return `M${x},${base}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${base}Z`
}

export default function TrendChart({
  title,
  dates,
  values,
  kind,
  format,
  summary,
  domain,
  reference,
}: Props) {
  const [boxRef, W] = useWidth<HTMLDivElement>()
  const [selected, setSelected] = useState<number | null>(null)

  const present = values.filter((v): v is number => v !== null)
  const extra = reference ? [reference.value] : []
  let [lo, hi] = domain ?? [
    kind === 'bar' ? 0 : Math.min(...present, ...extra),
    Math.max(...present, ...extra),
  ]
  // Одинаковые значения — линия посередине, а не на краю
  if (hi === lo) [lo, hi] = [lo - 1, hi + 1]

  const n = values.length
  const slot = W / n
  const base = H - PAD_BOTTOM
  const cx = (i: number) => slot * (i + 0.5)
  const y = (v: number) => PAD_TOP + ((hi - v) / (hi - lo)) * (base - PAD_TOP)

  // Линия рвётся на днях без данных: каждый непрерывный кусок — отдельный путь
  const segments: number[][] = []
  values.forEach((v, i) => {
    if (v === null) return
    const last = segments.at(-1)
    if (last && last.at(-1) === i - 1) last.push(i)
    else segments.push([i])
  })

  const pick = (clientX: number, el: SVGSVGElement) => {
    const left = el.getBoundingClientRect().left
    const i = Math.min(n - 1, Math.max(0, Math.floor((clientX - left) / slot)))
    setSelected(values[i] === null ? null : i)
  }

  const header =
    selected !== null && values[selected] !== null
      ? `${shortDate(dates[selected])} · ${format(values[selected])}`
      : summary
  const stroke = 'var(--color-button)'
  // За неделю столбики не должны становиться плитами — ограничиваем ширину
  const barW = Math.min(24, Math.max(1, slot - BAR_GAP))

  return (
    <section className="rounded-2xl bg-bg-secondary p-4">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="font-medium">{title}</h2>
        <span className="text-sm text-hint tabular-nums" aria-live="polite">
          {header}
        </span>
      </div>

      {/* Контейнер есть всегда: иначе ширина не измерится, когда данные появятся позже */}
      <div ref={boxRef} className="mt-3">
        {present.length === 0 ? (
          <p className="text-sm text-hint">Нет данных за этот период.</p>
        ) : (
          <>
            {W > 0 && (
            <svg
              width={W}
              height={H}
              className="block touch-pan-y"
              role="img"
              aria-label={`${title}: ${summary}`}
              onPointerDown={(e) => pick(e.clientX, e.currentTarget)}
              onPointerMove={(e) => pick(e.clientX, e.currentTarget)}
              onPointerLeave={(e) => e.pointerType === 'mouse' && setSelected(null)}
            >
              {/* Базовая линия и ориентир — приглушённые, чтобы не спорить с данными */}
              <line x1={0} x2={W} y1={base} y2={base} stroke="var(--color-hint)" strokeOpacity={0.3} />
              {reference && (
                <>
                  <line
                    x1={0}
                    x2={W}
                    y1={y(reference.value)}
                    y2={y(reference.value)}
                    stroke="var(--color-hint)"
                    strokeDasharray="4 4"
                  />
                  <text
                    x={W}
                    y={y(reference.value) - 4}
                    textAnchor="end"
                    className="fill-hint text-[11px]"
                  >
                    {reference.label}
                  </text>
                </>
              )}

              {selected !== null && (
                <line
                  x1={cx(selected)}
                  x2={cx(selected)}
                  y1={PAD_TOP}
                  y2={base}
                  stroke="var(--color-hint)"
                  strokeOpacity={0.5}
                />
              )}

              {kind === 'bar'
                ? values.map((v, i) =>
                    v === null || v <= lo ? null : (
                      <path
                        key={i}
                        d={barPath(cx(i) - barW / 2, y(v), barW, base)}
                        fill={stroke}
                        opacity={selected === null || selected === i ? 1 : 0.4}
                      />
                    ),
                  )
                : segments.map((seg) =>
                    seg.length === 1 ? (
                      <circle key={seg[0]} cx={cx(seg[0])} cy={y(values[seg[0]]!)} r={3} fill={stroke} />
                    ) : (
                      <polyline
                        key={seg[0]}
                        points={seg.map((i) => `${cx(i)},${y(values[i]!)}`).join(' ')}
                        fill="none"
                        stroke={stroke}
                        strokeWidth={2}
                        strokeLinejoin="round"
                        strokeLinecap="round"
                      />
                    ),
                  )}

              {kind === 'line' && selected !== null && values[selected] !== null && (
                <circle
                  cx={cx(selected)}
                  cy={y(values[selected]!)}
                  r={5}
                  fill={stroke}
                  stroke="var(--color-bg-secondary)"
                  strokeWidth={2}
                />
              )}
            </svg>
          )}
            <div className="mt-1 flex justify-between text-xs text-hint">
              <span>{shortDate(dates[0])}</span>
              <span>{shortDate(dates[n - 1])}</span>
            </div>
          </>
        )}
      </div>

      {/* Таблица для экранных чтецов: те же данные без графики */}
      <table className="sr-only">
        <caption>{title}</caption>
        <tbody>
          {values.map((v, i) =>
            v === null ? null : (
              <tr key={dates[i]}>
                <th scope="row">{shortDate(dates[i])}</th>
                <td>{format(v)}</td>
              </tr>
            ),
          )}
        </tbody>
      </table>
    </section>
  )
}
