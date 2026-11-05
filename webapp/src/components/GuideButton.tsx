/** Кнопка «Как делать» — значок «i» рядом с названием упражнения. */
export default function GuideButton({ name, onClick }: { name: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Как делать: ${name}`}
      className="flex size-9 shrink-0 items-center justify-center text-link"
    >
      <svg
        width="22"
        height="22"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9.5" />
        <path d="M12 11v6" />
        <circle cx="12" cy="7.5" r="0.6" fill="currentColor" />
      </svg>
    </button>
  )
}
