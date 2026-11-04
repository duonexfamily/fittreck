/** Поле числа в строку: подпись слева, значение справа. Значение — строка, как ввёл пользователь. */
export default function NumberInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <label className="flex items-baseline justify-between rounded-2xl bg-bg-secondary p-4">
      <span className="text-hint">{label}</span>
      <input
        type="number"
        inputMode="decimal"
        min={0}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-24 bg-transparent text-right text-lg font-semibold outline-none"
      />
    </label>
  )
}
