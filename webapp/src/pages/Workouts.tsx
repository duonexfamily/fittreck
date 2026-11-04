import { useMutation, useQuery } from '@tanstack/react-query'
import { useCallback } from 'react'
import { Link, useNavigate } from 'react-router'

import { type WorkoutSummary, createWorkout, getMe, getWorkouts } from '../api/client'
import { useBackButton } from '../hooks/useBackButton'
import { useMainButton } from '../hooks/useMainButton'
import { formatDay, shiftDate, todayIn } from '../lib/nutrition'
import { fmtNumber } from '../lib/workouts'
import { haptic } from '../lib/telegram'

// Сколько дней истории показывать
const HISTORY_DAYS = 90

function WorkoutCard({ w, today }: { w: WorkoutSummary; today: string }) {
  const stats = [
    w.set_count > 0 && `${w.set_count} подх.`,
    w.volume_kg > 0 && `${fmtNumber(w.volume_kg, 0)} кг`,
    w.rpe !== null && `RPE ${w.rpe}`,
  ].filter(Boolean)
  return (
    <li className="rounded-2xl bg-bg-secondary">
      <Link to={`/workouts/${w.id}`} className="block p-4">
        <div className="flex items-baseline justify-between gap-3">
          <span className="font-medium">{formatDay(w.date, today)}</span>
          {w.status === 'planned' && <span className="text-xs text-link">не завершена</span>}
        </div>
        <div className="mt-1 truncate text-sm">
          {w.exercise_names.length > 0 ? w.exercise_names.join(', ') : 'Пока без упражнений'}
        </div>
        {stats.length > 0 && <div className="mt-1 text-xs text-hint">{stats.join(' · ')}</div>}
      </Link>
    </li>
  )
}

export default function Workouts() {
  const navigate = useNavigate()
  const me = useQuery({ queryKey: ['me'], queryFn: getMe })
  const today = todayIn(me.data?.timezone)
  const from = shiftDate(today, -(HISTORY_DAYS - 1))

  const list = useQuery({
    queryKey: ['workouts', from, today],
    queryFn: () => getWorkouts(from, today),
    enabled: me.isSuccess,
  })

  useBackButton(useCallback(() => navigate('/'), [navigate]))

  const start = useMutation({
    mutationFn: () => createWorkout(today),
    onSuccess: (w) => {
      haptic.success()
      navigate(`/workouts/${w.id}`)
    },
    onError: () => haptic.error(),
  })
  const submit = useCallback(() => {
    if (me.isSuccess && !start.isPending) start.mutate()
  }, [me.isSuccess, start])
  useMainButton({
    text: 'Начать тренировку',
    onClick: submit,
    enabled: me.isSuccess,
    loading: start.isPending,
  })

  return (
    <main className="p-4 pb-10">
      <div className="flex items-baseline justify-between">
        <h1 className="text-xl font-semibold">Тренировки</h1>
        <Link to="/exercises" className="text-sm text-link">
          Каталог упражнений
        </Link>
      </div>

      {start.isError && <p className="mt-4 text-sm text-red-500">Не получилось начать.</p>}
      {list.isError && <p className="mt-4 text-hint">Не удалось загрузить тренировки.</p>}
      {list.isPending && <p className="mt-4 text-hint">Загрузка…</p>}
      {list.data?.length === 0 && (
        <p className="mt-4 text-hint">
          Здесь появятся ваши тренировки. Нажмите «Начать тренировку» внизу экрана.
        </p>
      )}
      {list.data && list.data.length > 0 && (
        <ul className="mt-4 grid gap-3">
          {list.data.map((w) => (
            <WorkoutCard key={w.id} w={w} today={today} />
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
