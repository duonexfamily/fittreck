import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router'

import {
  type Exercise,
  type SetValues,
  type Workout as WorkoutData,
  type WorkoutSet,
  addSet,
  createTemplate,
  deleteSet,
  deleteWorkout,
  getMe,
  getWorkout,
  updateSet,
  updateWorkout,
} from '../api/client'
import NumberInput from '../components/NumberInput'
import SliderField from '../components/SliderField'
import { useBackButton } from '../hooks/useBackButton'
import { useMainButton } from '../hooks/useMainButton'
import { formatDay, todayIn } from '../lib/nutrition'
import {
  EMPTY_SET_RAW,
  KIND_LABELS,
  MUSCLE_LABELS,
  type SetRaw,
  fmtNumber,
  fmtSet,
  parseSet,
  rpeHint,
  setToRaw,
  timeUnit,
} from '../lib/workouts'
import { haptic } from '../lib/telegram'

const DEFAULT_RPE = 6

/** Форма подхода: поля зависят от вида упражнения. Кнопки — свои, MainButton занят тренировкой. */
function SetForm({
  exercise,
  initial,
  submitText,
  pending,
  failed,
  onSubmit,
  onCancel,
  onDelete,
}: {
  exercise: Exercise
  initial: SetRaw
  submitText: string
  pending: boolean
  failed: boolean
  onSubmit: (v: SetValues) => void
  onCancel: () => void
  onDelete?: () => void
}) {
  const [raw, setRaw] = useState(initial)
  const values = parseSet(exercise.kind, raw)
  const field = (key: keyof SetRaw) => ({
    value: raw[key],
    onChange: (v: string) => setRaw({ ...raw, [key]: v }),
  })

  return (
    <div className="mt-2 grid gap-2">
      {exercise.kind === 'strength' ? (
        <>
          <NumberInput label="Повторения" placeholder="10" {...field('reps')} />
          <NumberInput label="Вес, кг" placeholder="без веса" {...field('weight')} />
        </>
      ) : (
        <NumberInput
          label={`Время, ${timeUnit(exercise.kind)}`}
          placeholder="0"
          {...field('time')}
        />
      )}
      {exercise.kind === 'cardio' && (
        <NumberInput label="Дистанция, км" placeholder="—" {...field('km')} />
      )}
      {failed && <p className="text-sm text-destructive">Не получилось сохранить.</p>}
      <div className="flex gap-2">
        <button
          type="button"
          disabled={!values || pending}
          onClick={() => values && onSubmit(values)}
          className="flex-1 rounded-xl bg-button p-3 font-medium text-button-text disabled:opacity-50"
        >
          {submitText}
        </button>
        <button type="button" onClick={onCancel} className="rounded-xl bg-bg p-3 text-hint">
          Отмена
        </button>
        {onDelete && (
          <button
            type="button"
            disabled={pending}
            onClick={onDelete}
            className="rounded-xl bg-bg p-3 text-destructive disabled:opacity-50"
            aria-label="Удалить подход"
          >
            Удалить
          </button>
        )}
      </div>
    </div>
  )
}

function ExerciseCard({
  workoutId,
  exercise,
  sets,
  startAdding,
}: {
  workoutId: number
  exercise: Exercise
  sets: WorkoutSet[]
  startAdding: boolean
}) {
  const queryClient = useQueryClient()
  // 'new' — добавляется подход, число — правится подход с этим id
  const [editing, setEditing] = useState<'new' | number | null>(startAdding ? 'new' : null)

  const onDone = async () => {
    haptic.success()
    setEditing(null)
    await queryClient.invalidateQueries({ queryKey: ['workout', workoutId] })
    await queryClient.invalidateQueries({ queryKey: ['workouts'] })
  }
  const save = useMutation({
    mutationFn: (v: SetValues) =>
      typeof editing === 'number'
        ? updateSet(editing, v)
        : addSet(workoutId, { ...v, exercise_id: exercise.id }),
    onSuccess: onDone,
    onError: () => haptic.error(),
  })
  const remove = useMutation({
    mutationFn: deleteSet,
    onSuccess: onDone,
    onError: () => haptic.error(),
  })
  // Подход из шаблона выполнен как запланировано — отметка одним касанием
  const check = useMutation({
    mutationFn: (s: WorkoutSet) => updateSet(s.id, { ...pickValues(s), done: true }),
    onSuccess: onDone,
    onError: () => haptic.error(),
  })

  const open = (target: 'new' | number) => {
    haptic.select()
    save.reset()
    setEditing(target)
  }
  const last = sets.at(-1)
  const form = (initial: SetRaw, submitText: string, onDelete?: () => void) => (
    <SetForm
      key={String(editing)}
      exercise={exercise}
      initial={initial}
      submitText={submitText}
      pending={save.isPending || remove.isPending}
      failed={save.isError || remove.isError}
      onSubmit={(v) => save.mutate(v)}
      onCancel={() => setEditing(null)}
      onDelete={onDelete}
    />
  )

  return (
    <section className="rounded-2xl bg-bg-secondary p-4">
      <h2 className="font-medium">{exercise.name}</h2>
      <div className="text-xs text-hint">
        {MUSCLE_LABELS[exercise.muscle_group]} · {KIND_LABELS[exercise.kind].hint}
      </div>
      {sets.length > 0 && (
        <ul className="mt-2 divide-y divide-bg">
          {sets.map((s) => (
            <li key={s.id} className="py-2">
              {editing === s.id ? (
                form(setToRaw(exercise.kind, s), 'Сохранить', () => remove.mutate(s.id))
              ) : (
                <div className="flex items-center gap-3">
                  {s.done ? (
                    <span className="w-6 shrink-0 text-center text-sm text-hint">{s.set_no}</span>
                  ) : (
                    <button
                      type="button"
                      disabled={check.isPending}
                      onClick={() => check.mutate(s)}
                      className="size-6 shrink-0 rounded-full border-2 border-link disabled:opacity-50"
                      aria-label={`Отметить подход ${s.set_no} выполненным`}
                    />
                  )}
                  <button
                    type="button"
                    onClick={() => open(s.id)}
                    className={`flex-1 text-left ${s.done ? '' : 'text-hint'}`}
                  >
                    {fmtSet(s)}
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {check.isError && <p className="mt-1 text-sm text-destructive">Не получилось отметить.</p>}
      {editing === 'new' ? (
        // Следующий подход начинается с прошлых значений — обычно меняется одна цифра
        form(last ? setToRaw(exercise.kind, last) : EMPTY_SET_RAW, 'Добавить подход')
      ) : (
        <button
          type="button"
          onClick={() => open('new')}
          className="mt-2 text-sm font-medium text-link"
        >
          + Подход
        </button>
      )}
    </section>
  )
}

const pickValues = ({ reps, weight_kg, duration_s, distance_m }: SetValues): SetValues => ({
  reps,
  weight_kg,
  duration_s,
  distance_m,
})

/** Сохранить тренировку как шаблон: упражнения и подходы с их значениями. */
function SaveTemplate({ workoutId }: { workoutId: number }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState<string | null>(null)
  const save = useMutation({
    mutationFn: (n: string) => createTemplate({ name: n, workout_id: workoutId }),
    onSuccess: async () => {
      haptic.success()
      setName(null)
      await queryClient.invalidateQueries({ queryKey: ['templates'] })
    },
    onError: () => haptic.error(),
  })

  if (name === null) {
    return (
      <button
        type="button"
        onClick={() => {
          haptic.select()
          save.reset()
          setName('')
        }}
        className="rounded-2xl bg-bg-secondary p-4 text-center font-medium text-link"
      >
        {save.isSuccess ? 'Шаблон сохранён ✓' : 'Сохранить как шаблон'}
      </button>
    )
  }
  const trimmed = name.trim()
  return (
    <section className="rounded-2xl bg-bg-secondary p-4">
      <h2 className="font-medium">Новый шаблон</h2>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        maxLength={64}
        placeholder="Название, например «Ноги»"
        className="mt-2 w-full rounded-xl bg-bg p-3 outline-none"
      />
      {save.isError && <p className="mt-2 text-sm text-destructive">Не получилось сохранить.</p>}
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          disabled={!trimmed || save.isPending}
          onClick={() => save.mutate(trimmed)}
          className="flex-1 rounded-xl bg-button p-3 font-medium text-button-text disabled:opacity-50"
        >
          Сохранить
        </button>
        <button
          type="button"
          onClick={() => setName(null)}
          className="rounded-xl bg-bg p-3 text-hint"
        >
          Отмена
        </button>
      </div>
    </section>
  )
}

/** MainButton монтируется только когда нужен: хук показывает кнопку, размонтирование — прячет. */
function MainAction(props: Parameters<typeof useMainButton>[0]) {
  useMainButton(props)
  return null
}

function Outcome({ workout, onSaved }: { workout: WorkoutData; onSaved: () => void }) {
  const [rpe, setRpe] = useState(workout.rpe ?? DEFAULT_RPE)
  const [note, setNote] = useState(workout.note ?? '')
  const finishing = workout.status === 'planned'
  const save = useMutation({
    mutationFn: () =>
      updateWorkout(workout.id, {
        ...(finishing && { status: 'done' as const }),
        rpe,
        note: note.trim() || null,
      }),
    onSuccess: onSaved,
    onError: () => haptic.error(),
  })
  const submit = useCallback(() => {
    if (!save.isPending) save.mutate()
  }, [save])

  return (
    <section className="rounded-2xl bg-bg-secondary p-4">
      <h2 className="font-medium">{finishing ? 'Завершение тренировки' : 'Оценка тренировки'}</h2>
      <div className="mt-3">
        <SliderField
          label="Нагрузка (RPE)"
          unit=""
          value={rpe}
          min={1}
          max={10}
          step={1}
          onChange={setRpe}
        />
        <p className="mt-1 px-1 text-xs text-hint">
          {rpe} из 10 — {rpeHint(rpe)}. Насколько тяжело было в целом.
        </p>
      </div>
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        maxLength={1000}
        rows={3}
        placeholder="Заметка: самочувствие, что получилось"
        className="mt-3 w-full resize-none rounded-xl bg-bg p-3 outline-none"
      />
      {save.isError && <p className="mt-2 text-sm text-destructive">Не получилось сохранить.</p>}
      <MainAction text="Сохранить" onClick={submit} loading={save.isPending} />
    </section>
  )
}

export default function Workout() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const id = Number(useParams().id)
  // Упражнение, выбранное в каталоге: показывается, пока у него нет подходов
  const picked = (useLocation().state as { exercise?: Exercise } | null)?.exercise
  const [outcomeOpen, setOutcomeOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const me = useQuery({ queryKey: ['me'], queryFn: getMe })
  const workout = useQuery({
    queryKey: ['workout', id],
    queryFn: () => getWorkout(id),
    enabled: Number.isInteger(id) && id > 0,
  })

  // Назад — в календарь на день тренировки
  const day = workout.data?.date
  const toList = useCallback(
    () => navigate(day ? `/workouts?day=${day}` : '/workouts', { replace: true }),
    [navigate, day],
  )
  useBackButton(toList)

  const remove = useMutation({
    mutationFn: () => deleteWorkout(id),
    onSuccess: async () => {
      haptic.success()
      await queryClient.invalidateQueries({ queryKey: ['workouts'] })
      toList()
    },
    onError: () => haptic.error(),
  })

  const openOutcome = useCallback(() => {
    haptic.select()
    setOutcomeOpen(true)
  }, [])

  if (!Number.isInteger(id) || id <= 0) return <Navigate to="/workouts" replace />
  if (workout.isError) {
    return (
      <main className="p-4">
        <p className="text-hint">Не удалось загрузить тренировку.</p>
      </main>
    )
  }
  if (!workout.data) return <p className="p-4 text-hint">Загрузка…</p>

  const w = workout.data
  const today = todayIn(me.data?.timezone)
  const blocks = [...w.exercises]
  if (picked && !blocks.some((b) => b.exercise.id === picked.id)) {
    blocks.push({ exercise: picked, sets: [] })
  }
  const hasSets = w.exercises.length > 0
  const hasDone = w.exercises.some((b) => b.sets.some((s) => s.done))
  const hasPlannedSets = w.exercises.some((b) => b.sets.some((s) => !s.done))
  const statusLabel = w.status === 'done' ? 'Выполнена' : w.date > today ? 'Запланирована' : 'Идёт'

  const onSaved = async () => {
    haptic.success()
    setOutcomeOpen(false)
    await queryClient.invalidateQueries({ queryKey: ['workout', id] })
    await queryClient.invalidateQueries({ queryKey: ['workouts'] })
    if (w.status === 'planned') toList()
  }

  return (
    <main className="p-4 pb-10">
      <div className="flex items-baseline justify-between gap-3">
        <h1 className="text-xl font-semibold">{formatDay(w.date, today)}</h1>
        <span className={`text-sm ${w.status === 'done' ? 'text-hint' : 'text-link'}`}>
          {statusLabel}
        </span>
      </div>
      {w.volume_kg > 0 && (
        <p className="mt-1 text-sm text-hint">Объём: {fmtNumber(w.volume_kg, 0)} кг</p>
      )}
      {hasPlannedSets && (
        <p className="mt-1 text-sm text-hint">
          Отмечайте подходы кружком по ходу тренировки. Неотмеченные не входят в объём.
        </p>
      )}

      <div className="mt-4 grid gap-3">
        {blocks.map((b) => (
          <ExerciseCard
            key={b.exercise.id}
            workoutId={w.id}
            exercise={b.exercise}
            sets={b.sets}
            startAdding={b.sets.length === 0}
          />
        ))}
        <Link
          to={`/exercises?pick=${w.id}`}
          className="rounded-2xl bg-bg-secondary p-4 text-center font-medium text-link"
        >
          + Упражнение
        </Link>
        {hasSets && <SaveTemplate workoutId={w.id} />}

        {outcomeOpen ? (
          <Outcome workout={w} onSaved={onSaved} />
        ) : (
          w.status === 'done' && (
            <section className="rounded-2xl bg-bg-secondary p-4">
              <div className="flex items-baseline justify-between">
                <h2 className="font-medium">
                  {w.rpe !== null ? `RPE ${w.rpe} — ${rpeHint(w.rpe)}` : 'Без оценки'}
                </h2>
                <button type="button" onClick={openOutcome} className="text-sm text-link">
                  Изменить
                </button>
              </div>
              {w.note && <p className="mt-1 text-sm whitespace-pre-line">{w.note}</p>}
            </section>
          )
        )}
      </div>

      {w.status === 'planned' && !outcomeOpen && (
        <MainAction text="Завершить тренировку" onClick={openOutcome} enabled={hasDone} />
      )}

      <button
        type="button"
        disabled={remove.isPending}
        onClick={() => (confirmDelete ? remove.mutate() : setConfirmDelete(true))}
        className="mt-6 w-full rounded-2xl bg-bg-secondary p-4 font-medium text-destructive disabled:opacity-50"
      >
        {confirmDelete ? 'Точно удалить? Нажмите ещё раз' : 'Удалить тренировку'}
      </button>
      {remove.isError && <p className="mt-4 text-sm text-destructive">Не получилось удалить.</p>}
    </main>
  )
}
