import type { Exercise } from '../api/client'
import { useMainButton } from '../hooks/useMainButton'
import { ANIMS } from '../lib/exerciseAnims'
import { GUIDES } from '../lib/exerciseGuides'
import { KIND_LABELS, MUSCLE_LABELS } from '../lib/workouts'
import { haptic, openLink } from '../lib/telegram'
import ExerciseFigure from './ExerciseFigure'

const VIDEO_SEARCH = [
  { label: 'Видео на Rutube', url: 'https://rutube.ru/search/?query=' },
  { label: 'Видео на YouTube', url: 'https://www.youtube.com/results?search_query=' },
]

/**
 * Карточка техники: анимированная схема, шаги, частые ошибки и поиск видео.
 * Открывается поверх экрана. «Назад» обрабатывает экран-владелец и вызывает onClose.
 */
export default function ExerciseGuide({
  exercise,
  onClose,
}: {
  exercise: Exercise
  onClose: () => void
}) {
  useMainButton({ text: 'Понятно', onClick: onClose })
  const guide = GUIDES[exercise.name]
  const query = encodeURIComponent(`${exercise.name} техника выполнения`)

  return (
    <div className="fixed inset-0 z-40 overflow-y-auto bg-bg">
      <main className="p-4 pb-10">
        <h1 className="text-xl font-semibold">{exercise.name}</h1>
        <p className="text-sm text-hint">
          {guide?.muscles ??
            (exercise.kind === 'strength'
              ? MUSCLE_LABELS[exercise.muscle_group]
              : KIND_LABELS[exercise.kind].label)}
        </p>

        {guide ? (
          <>
            <div className="mt-3 rounded-2xl bg-bg-secondary p-2">
              <ExerciseFigure anim={ANIMS[guide.anim]} label={`Схема: ${exercise.name}`} />
            </div>

            <h2 className="mt-5 font-semibold">Как выполнять</h2>
            <ol className="mt-2 grid gap-2">
              {guide.steps.map((s, i) => (
                <li key={s} className="flex gap-3">
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-bg-secondary text-sm font-medium text-link">
                    {i + 1}
                  </span>
                  <span>{s}</span>
                </li>
              ))}
            </ol>

            <h2 className="mt-5 font-semibold">Частые ошибки</h2>
            <ul className="mt-2 grid gap-1.5">
              {guide.mistakes.map((m) => (
                <li key={m} className="flex gap-3">
                  <span className="w-6 shrink-0 text-center text-destructive">✕</span>
                  <span>{m}</span>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="mt-4 text-hint">
            Для этого упражнения схемы нет. Технику можно посмотреть в видео.
          </p>
        )}

        <div className="mt-5 grid grid-cols-2 gap-2">
          {VIDEO_SEARCH.map((v) => (
            <button
              key={v.label}
              type="button"
              onClick={() => {
                haptic.select()
                openLink(v.url + query)
              }}
              className="rounded-2xl bg-bg-secondary p-3 text-sm font-medium text-link"
            >
              {v.label}
            </button>
          ))}
        </div>

        <p className="mt-5 text-xs text-hint">
          Схема упрощённая. Начинайте с лёгкого веса. При боли остановитесь. Если есть травмы
          или болезни, сначала посоветуйтесь с врачом или тренером.
        </p>
      </main>
    </div>
  )
}
