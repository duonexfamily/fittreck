import { useEffect, useState } from 'react'

import { type Anim, type Prim, VIEW_BOX, drawAt } from '../lib/figure'

// Цвета — только из темы Telegram
const STROKE: Record<Prim['role'], string> = {
  body: 'var(--color-text)',
  far: 'var(--color-hint)',
  scene: 'var(--color-hint)',
  prop: 'var(--color-link)',
}
const OPACITY: Record<Prim['role'], number> = { body: 1, far: 0.6, scene: 0.45, prop: 1 }

const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

/** Анимированная схема упражнения. При «уменьшить движение» — статичная поза. */
export default function ExerciseFigure({ anim, label }: { anim: Anim; label: string }) {
  // Без анимации показываем вторую позу — в ней обычно видно усилие
  const [t, setT] = useState(() => anim.ms ?? 1100)

  useEffect(() => {
    if (reducedMotion()) return
    let frame = 0
    const start = performance.now()
    const tick = (now: number) => {
      setT(now - start)
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [anim])

  return (
    <svg viewBox={VIEW_BOX} role="img" aria-label={label} className="mx-auto block h-auto w-full max-w-sm">
      {drawAt(anim, t).map((p, i) => {
        const stroke = STROKE[p.role]
        const opacity = OPACITY[p.role]
        if (p.k === 'line') {
          const [x1, y1, x2, y2] = p.p
          return (
            <line
              key={i}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke={stroke}
              strokeOpacity={opacity}
              strokeWidth={p.w}
              strokeLinecap="round"
            />
          )
        }
        if (p.k === 'circle') {
          const [cx, cy, r] = p.p
          return p.fill ? (
            <circle key={i} cx={cx} cy={cy} r={r} fill={stroke} fillOpacity={opacity} />
          ) : (
            <circle
              key={i}
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={stroke}
              strokeOpacity={opacity}
              strokeWidth={p.w}
            />
          )
        }
        return (
          <path
            key={i}
            d={p.d}
            fill="none"
            stroke={stroke}
            strokeOpacity={opacity}
            strokeWidth={p.w}
          />
        )
      })}
    </svg>
  )
}
