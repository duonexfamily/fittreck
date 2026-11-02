interface Props {
  label: string
  unit: string
  value: number
  min: number
  max: number
  step: number
  onChange: (value: number) => void
}

/** Слайдер с крупным значением. Точное число можно ввести и с клавиатуры. */
export default function SliderField({ label, unit, value, min, max, step, onChange }: Props) {
  const clamp = (v: number) => Math.min(max, Math.max(min, v))
  return (
    <div className="rounded-2xl bg-bg-secondary p-4">
      <div className="flex items-baseline justify-between">
        <span className="text-hint">{label}</span>
        <span>
          <input
            type="number"
            inputMode="decimal"
            value={value}
            min={min}
            max={max}
            step={step}
            onChange={(e) => {
              const v = Number(e.target.value)
              if (!Number.isNaN(v)) onChange(v)
            }}
            onBlur={() => onChange(clamp(value))}
            className="w-20 bg-transparent text-right text-2xl font-semibold outline-none"
            aria-label={label}
          />
          <span className="ml-1 text-hint">{unit}</span>
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={clamp(value)}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-3 w-full accent-button"
        aria-hidden="true"
        tabIndex={-1}
      />
    </div>
  )
}
