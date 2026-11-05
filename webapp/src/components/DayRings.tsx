import { useEffect, useState } from 'react'

export interface Ring {
  // Доля выполнения: 0…1, больше 1 рисуется полным кольцом
  value: number
  // CSS-цвет кольца, производный от темы (var(--hue-food) и т. п.)
  color: string
  label: string
}

const SIZE = 148
const STROKE = 14
const GAP = 3

/** Концентрические кольца прогресса дня. Первое кольцо — внешнее. */
export default function DayRings({ rings }: { rings: Ring[] }) {
  // Сначала рисуем пустые кольца, на следующем кадре — заполненные: так срабатывает анимация
  const [drawn, setDrawn] = useState(false)
  useEffect(() => {
    const id = requestAnimationFrame(() => setDrawn(true))
    return () => cancelAnimationFrame(id)
  }, [])

  const c = SIZE / 2
  return (
    <svg
      width={SIZE}
      height={SIZE}
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      role="img"
      aria-label={rings.map((r) => `${r.label}: ${Math.round(r.value * 100)}%`).join(', ')}
      className="shrink-0 -rotate-90 overflow-visible"
    >
      {rings.map((ring, i) => {
        const r = c - STROKE / 2 - i * (STROKE + GAP)
        const len = 2 * Math.PI * r
        const share = Math.min(Math.max(ring.value, 0), 1)
        return (
          <g key={ring.label} fill="none" strokeWidth={STROKE} strokeLinecap="round">
            <circle cx={c} cy={c} r={r} stroke={ring.color} strokeOpacity={0.16} />
            {share > 0 && (
              <circle
                className="ring-progress"
                cx={c}
                cy={c}
                r={r}
                stroke={ring.color}
                strokeDasharray={len}
                strokeDashoffset={drawn ? len * (1 - share) : len}
                style={{ filter: `drop-shadow(0 0 3px ${ring.color})` }}
              />
            )}
          </g>
        )
      })}
    </svg>
  )
}
