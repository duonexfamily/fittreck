/** Загрузка экрана: кольцо в цвет кнопки темы. */
export default function Loader() {
  return (
    <div className="flex justify-center p-10" role="status" aria-label="Загрузка">
      <svg width="36" height="36" viewBox="0 0 36 36" className="loader-ring">
        <circle cx="18" cy="18" r="14" fill="none" stroke="var(--accent)" strokeOpacity="0.18" strokeWidth="5" />
        <circle
          cx="18"
          cy="18"
          r="14"
          fill="none"
          stroke="var(--accent)"
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray="30 88"
        />
      </svg>
    </div>
  )
}
