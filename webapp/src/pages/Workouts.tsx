import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'

import {
  type Template,
  type Workout,
  type WorkoutSummary,
  createWorkout,
  deleteTemplate,
  getMe,
  getTemplates,
  getWorkouts,
  startTemplate,
} from '../api/client'
import Calendar, { type DayMark, monthRange } from '../components/Calendar'
import { useBackButton } from '../hooks/useBackButton'
import { useMainButton } from '../hooks/useMainButton'
import { formatDay, todayIn } from '../lib/nutrition'
import { fmtNumber } from '../lib/workouts'
import { haptic } from '../lib/telegram'

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/

function WorkoutCard({ w, today }: { w: WorkoutSummary; today: string }) {
  const stats = [
    w.set_count > 0 && `${w.set_count} подх.`,
    w.volume_kg > 0 && `${fmtNumber(w.volume_kg, 0)} кг`,
    w.rpe !== null && `RPE ${w.rpe}`,
  ].filter(Boolean)
  const state = w.status === 'done' ? null : w.date > today ? 'запланирована' : 'не завершена'
  return (
    <li className="rounded-2xl bg-bg-secondary">
      <Link to={`/workouts/${w.id}`} className="block p-4">
        <div className="flex items-baseline justify-between gap-3">
          <span className="min-w-0 truncate font-medium">
            {w.exercise_names.length > 0 ? w.exercise_names.join(', ') : 'Пока без упражнений'}
          </span>
          {state && <span className="shrink-0 text-xs text-link">{state}</span>}
        </div>
        {stats.length > 0 && <div className="mt-1 text-xs text-hint">{stats.join(' · ')}</div>}
      </Link>
    </li>
  )
}

function TemplateCard({
  t,
  actionText,
  pending,
  onStart,
}: {
  t: Template
  actionText: string
  pending: boolean
  onStart: () => void
}) {
  const queryClient = useQueryClient()
  const [confirm, setConfirm] = useState(false)
  const remove = useMutation({
    mutationFn: () => deleteTemplate(t.id),
    onSuccess: async () => {
      haptic.success()
      await queryClient.invalidateQueries({ queryKey: ['templates'] })
    },
    onError: () => haptic.error(),
  })
  return (
    <li className="rounded-2xl bg-bg-secondary p-4">
      <div className="flex items-baseline justify-between gap-3">
        <span className="min-w-0 truncate font-medium">{t.name}</span>
        <button
          type="button"
          disabled={remove.isPending}
          onClick={() => (confirm ? remove.mutate() : setConfirm(true))}
          className="shrink-0 text-xs text-destructive disabled:opacity-50"
        >
          {confirm ? 'Точно удалить?' : 'Удалить'}
        </button>
      </div>
      <div className="mt-1 truncate text-sm text-hint">
        {t.exercise_names.join(', ')} · {t.set_count} подх.
      </div>
      <button
        type="button"
        disabled={pending}
        onClick={onStart}
        className="mt-3 w-full rounded-xl bg-button p-3 font-medium text-button-text disabled:opacity-50"
      >
        {actionText}
      </button>
    </li>
  )
}

export default function Workouts() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const me = useQuery({ queryKey: ['me'], queryFn: getMe })
  const today = todayIn(me.data?.timezone)

  // Выбранный день — в адресе, чтобы вернуться к нему из тренировки
  const dayParam = params.get('day')
  const selected = dayParam && DATE_RE.test(dayParam) ? dayParam : today
  const [month, setMonth] = useState<string | null>(null)
  const shownMonth = month ?? selected.slice(0, 7)
  const { from, to } = monthRange(shownMonth)

  const list = useQuery({
    queryKey: ['workouts', from, to],
    queryFn: () => getWorkouts(from, to),
    enabled: me.isSuccess,
  })
  const templates = useQuery({ queryKey: ['templates'], queryFn: getTemplates })

  useBackButton(useCallback(() => navigate('/'), [navigate]))

  const select = (date: string) => {
    setParams({ day: date }, { replace: true })
    setMonth(date.slice(0, 7))
  }

  const marks: Record<string, DayMark> = {}
  for (const w of list.data ?? []) {
    const mark = (marks[w.date] ??= { done: false, planned: false })
    if (w.status === 'done') mark.done = true
    else mark.planned = true
  }
  const dayWorkouts = (list.data ?? []).filter((w) => w.date === selected)
  const future = selected > today
  const doneInMonth = (list.data ?? []).filter((w) => w.status === 'done').length

  const opened = (w: Workout) => {
    haptic.success()
    navigate(`/workouts/${w.id}`)
  }
  const start = useMutation({
    mutationFn: () => createWorkout(selected),
    onSuccess: opened,
    onError: () => haptic.error(),
  })
  const fromTemplate = useMutation({
    mutationFn: (id: number) => startTemplate(id, selected),
    onSuccess: opened,
    onError: () => haptic.error(),
  })
  const busy = start.isPending || fromTemplate.isPending
  const submit = useCallback(() => {
    if (me.isSuccess && !busy) start.mutate()
  }, [me.isSuccess, busy, start])
  useMainButton({
    text: future ? 'Запланировать тренировку' : 'Начать тренировку',
    onClick: submit,
    enabled: me.isSuccess,
    loading: start.isPending,
  })

  return (
    <main className="p-4 pb-10">
      <div className="flex items-baseline justify-between">
        <h1 className="page-title">Тренировки</h1>
        <Link to="/exercises" className="text-sm text-link">
          Каталог упражнений
        </Link>
      </div>

      <div className="mt-4">
        <Calendar
          month={shownMonth}
          today={today}
          selected={selected}
          marks={marks}
          onSelect={select}
          onMonth={setMonth}
        />
        {list.data && (
          <p className="mt-2 px-1 text-xs text-hint">Выполнено за месяц: {doneInMonth}</p>
        )}
      </div>

      <h2 className="mt-6 font-medium">{formatDay(selected, today)}</h2>
      {(start.isError || fromTemplate.isError) && (
        <p className="mt-2 text-sm text-destructive">Не получилось создать тренировку.</p>
      )}
      {list.isError && <p className="mt-2 text-hint">Не удалось загрузить тренировки.</p>}
      {list.isPending && <p className="mt-2 text-hint">Загрузка…</p>}
      {list.data && dayWorkouts.length === 0 && (
        <p className="mt-2 text-sm text-hint">
          {future
            ? 'Тренировок в плане нет. Запланируйте её кнопкой внизу или по шаблону.'
            : 'Тренировок нет. Начните её кнопкой внизу или по шаблону.'}
        </p>
      )}
      {dayWorkouts.length > 0 && (
        <ul className="mt-2 grid gap-3">
          {dayWorkouts.map((w) => (
            <WorkoutCard key={w.id} w={w} today={today} />
          ))}
        </ul>
      )}

      <h2 className="mt-6 font-medium">Шаблоны</h2>
      {templates.isError && <p className="mt-2 text-hint">Не удалось загрузить шаблоны.</p>}
      {templates.data?.length === 0 && (
        <p className="mt-2 text-sm text-hint">
          Откройте тренировку и нажмите «Сохранить как шаблон» — потом её можно повторить в один
          клик.
        </p>
      )}
      {templates.data && templates.data.length > 0 && (
        <ul className="mt-2 grid gap-3">
          {templates.data.map((t) => (
            <TemplateCard
              key={t.id}
              t={t}
              actionText={future ? 'Запланировать' : 'Начать'}
              pending={busy}
              onStart={() => fromTemplate.mutate(t.id)}
            />
          ))}
        </ul>
      )}

      <p className="mt-6 text-xs text-hint">
        Приложение носит информационный характер и не заменяет консультацию врача или тренера.
        Подбирайте нагрузку по самочувствию.
      </p>
    </main>
  )
}
