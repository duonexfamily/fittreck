import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Suspense, lazy, useCallback, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'

import {
  type Exercise,
  type ExerciseKind,
  type MuscleGroup,
  createExercise,
  searchExercises,
} from '../api/client'
import ChoiceGroup from '../components/ChoiceGroup'
import GuideButton from '../components/GuideButton'
import { useBackButton } from '../hooks/useBackButton'
import { useDebounced } from '../hooks/useDebounced'
import { useMainButton } from '../hooks/useMainButton'
import { EXERCISE_KINDS, KIND_LABELS, MUSCLE_GROUPS, MUSCLE_LABELS } from '../lib/workouts'
import { haptic } from '../lib/telegram'

const ExerciseGuide = lazy(() => import('../components/ExerciseGuide'))

interface Filter {
  label: string
  muscle?: MuscleGroup
  kind?: ExerciseKind
}

// Кардио и «на время» — по виду упражнения, остальное — по группе мышц
const FILTERS: Filter[] = [
  { label: 'Все' },
  ...MUSCLE_GROUPS.map((muscle) => ({ label: MUSCLE_LABELS[muscle], muscle })),
  { label: KIND_LABELS.cardio.label, kind: 'cardio' },
  { label: KIND_LABELS.stretch.label, kind: 'stretch' },
]

const MUSCLE_OPTIONS = MUSCLE_GROUPS.map((value) => ({ value, label: MUSCLE_LABELS[value] }))
const KIND_OPTIONS = EXERCISE_KINDS.map((value) => ({ value, ...KIND_LABELS[value] }))

function CreateExercise({
  initialName,
  onCreated,
}: {
  initialName: string
  onCreated: (e: Exercise) => void
}) {
  const [name, setName] = useState(initialName)
  const [muscle, setMuscle] = useState<MuscleGroup | null>(null)
  const [kind, setKind] = useState<ExerciseKind>('strength')
  const create = useMutation({
    mutationFn: createExercise,
    onSuccess: onCreated,
    onError: () => haptic.error(),
  })

  const valid = name.trim().length > 0 && muscle !== null
  const submit = useCallback(() => {
    if (valid && muscle && !create.isPending) {
      create.mutate({ name: name.trim(), muscle_group: muscle, kind })
    }
  }, [valid, muscle, create, name, kind])
  useMainButton({ text: 'Сохранить', onClick: submit, enabled: valid, loading: create.isPending })

  return (
    <section className="mt-4 grid gap-3">
      <h2 className="text-lg font-semibold">Своё упражнение</h2>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        maxLength={128}
        placeholder="Название"
        className="w-full rounded-2xl bg-bg-secondary p-4 outline-none"
      />
      <h3 className="text-sm text-hint">Группа мышц</h3>
      <ChoiceGroup options={MUSCLE_OPTIONS} value={muscle} onChange={setMuscle} />
      <h3 className="text-sm text-hint">Как записывать подходы</h3>
      <ChoiceGroup options={KIND_OPTIONS} value={kind} onChange={setKind} columns={1} />
      {create.isError && <p className="text-sm text-destructive">Не получилось сохранить.</p>}
    </section>
  )
}

export default function Exercises() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [params] = useSearchParams()
  // ?pick=<id тренировки> — выбор упражнения для тренировки
  const pick = Number(params.get('pick')) || null

  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<Filter>(FILTERS[0])
  const [creating, setCreating] = useState(false)
  // Открытая карточка техники
  const [guide, setGuide] = useState<Exercise | null>(null)
  const q = useDebounced(query.trim(), 300)

  const list = useQuery({
    queryKey: ['exercises', q, filter.muscle, filter.kind],
    queryFn: () => searchExercises({ query: q, muscle: filter.muscle, kind: filter.kind }),
    placeholderData: (prev) => prev,
  })

  const back = useCallback(() => {
    if (guide) setGuide(null)
    else if (creating) setCreating(false)
    else navigate(pick ? `/workouts/${pick}` : '/workouts', { replace: true })
  }, [guide, creating, navigate, pick])
  useBackButton(back)

  const select = (e: Exercise) => {
    haptic.select()
    if (pick) navigate(`/workouts/${pick}`, { replace: true, state: { exercise: e } })
  }

  const openGuide = (e: Exercise) => {
    haptic.select()
    setGuide(e)
  }
  const closeGuide = useCallback(() => setGuide(null), [])

  const onCreated = async (e: Exercise) => {
    haptic.success()
    await queryClient.invalidateQueries({ queryKey: ['exercises'] })
    if (pick) select(e)
    else setCreating(false)
  }

  if (creating) {
    return (
      <main className="p-4 pb-10">
        <CreateExercise initialName={query.trim()} onCreated={onCreated} />
      </main>
    )
  }

  return (
    <main className="p-4 pb-10">
      <h1 className="page-title">{pick ? 'Выберите упражнение' : 'Упражнения'}</h1>
      <p className="mt-1 text-sm text-hint">
        {pick
          ? 'Значок «i» — как делать упражнение.'
          : 'Нажмите на упражнение, чтобы посмотреть технику.'}
      </p>
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Найти упражнение"
        maxLength={64}
        className="mt-3 w-full rounded-2xl bg-bg-secondary p-4 text-lg outline-none"
      />
      <div className="-mx-4 mt-3 flex gap-2 overflow-x-auto px-4 pb-1">
        {FILTERS.map((f) => (
          <button
            key={f.label}
            type="button"
            onClick={() => {
              haptic.select()
              setFilter(f)
            }}
            className={`shrink-0 rounded-full px-3 py-1.5 text-sm ${
              f === filter ? 'bg-button text-button-text' : 'bg-bg-secondary'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {list.isError && <p className="mt-4 text-hint">Не удалось загрузить каталог.</p>}
      {list.data?.length === 0 && <p className="mt-4 text-hint">Ничего не нашлось.</p>}
      {list.data && list.data.length > 0 && (
        <ul className="mt-2 divide-y divide-bg-secondary">
          {list.data.map((e) => {
            const body = (
              <>
                <span className="min-w-0 truncate">
                  {e.name}
                  {e.own && <span className="ml-2 text-xs text-hint">своё</span>}
                </span>
                <span className="shrink-0 text-xs text-hint">
                  {e.kind === 'strength'
                    ? MUSCLE_LABELS[e.muscle_group]
                    : KIND_LABELS[e.kind].label}
                </span>
              </>
            )
            return (
              <li key={e.id} className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => (pick ? select(e) : openGuide(e))}
                  className="flex min-w-0 flex-1 items-baseline justify-between gap-3 py-3 text-left"
                >
                  {body}
                </button>
                {pick && <GuideButton name={e.name} onClick={() => openGuide(e)} />}
              </li>
            )
          })}
        </ul>
      )}

      <button
        type="button"
        onClick={() => {
          haptic.select()
          setCreating(true)
        }}
        className="mt-4 w-full rounded-2xl bg-bg-secondary p-4 font-medium text-link"
      >
        + Своё упражнение
      </button>

      {guide && (
        <Suspense fallback={null}>
          <ExerciseGuide exercise={guide} onClose={closeGuide} />
        </Suspense>
      )}
    </main>
  )
}
