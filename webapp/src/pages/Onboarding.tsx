import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router'

import {
  type Activity,
  type Goal,
  type Me,
  type Sex,
  getMe,
  getTargets,
  putProfile,
} from '../api/client'
import ChoiceGroup from '../components/ChoiceGroup'
import SliderField from '../components/SliderField'
import { useBackButton } from '../hooks/useBackButton'
import { useMainButton } from '../hooks/useMainButton'
import { haptic } from '../lib/telegram'

const SEX_OPTIONS: { value: Sex; label: string }[] = [
  { value: 'male', label: 'Мужской' },
  { value: 'female', label: 'Женский' },
]

const GOAL_OPTIONS: { value: Goal; label: string; hint: string }[] = [
  { value: 'lose', label: 'Похудеть', hint: 'Небольшой дефицит калорий' },
  { value: 'maintain', label: 'Поддерживать', hint: 'Сохранить текущий вес' },
  { value: 'gain', label: 'Набрать массу', hint: 'Небольшой профицит' },
]

const ACTIVITY_OPTIONS: { value: Activity; label: string; hint: string }[] = [
  { value: 'sedentary', label: 'Минимальная', hint: 'Сидячая работа, без тренировок' },
  { value: 'light', label: 'Низкая', hint: 'Тренировки 1–3 раза в неделю' },
  { value: 'moderate', label: 'Средняя', hint: 'Тренировки 3–5 раз в неделю' },
  { value: 'active', label: 'Высокая', hint: 'Тренировки 6–7 раз в неделю' },
  { value: 'very_active', label: 'Очень высокая', hint: 'Физическая работа и тренировки' },
]

// Границы совпадают с проверкой на backend (app/api/schemas/me.py)
const MIN_AGE = 14
const MAX_AGE = 100

function yearsAgo(years: number): string {
  const d = new Date()
  d.setFullYear(d.getFullYear() - years)
  return d.toISOString().slice(0, 10)
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <h2 className="mb-2 text-sm font-medium text-hint">{title}</h2>
      {children}
    </section>
  )
}

export default function Onboarding() {
  const me = useQuery({ queryKey: ['me'], queryFn: getMe })
  const onboarded = Boolean(me.data?.onboarded_at)
  const targets = useQuery({ queryKey: ['targets'], queryFn: getTargets, enabled: onboarded })

  // Форма берёт начальные значения один раз — ждём данные, иначе поля останутся пустыми
  if (me.isError || targets.isError) {
    return <p className="p-4 text-hint">Не удалось загрузить анкету. Попробуйте открыть заново.</p>
  }
  if (!me.data || (onboarded && !targets.data)) {
    return <p className="p-4 text-hint">Загрузка…</p>
  }
  return <OnboardingForm me={me.data} weightKg={targets.data?.weight_kg} />
}

function OnboardingForm({ me, weightKg }: { me: Me; weightKg?: string }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const onboarded = Boolean(me.onboarded_at)

  // Повторное заполнение — подставляем сохранённые значения
  const [sex, setSex] = useState<Sex | null>(me.sex)
  const [birthDate, setBirthDate] = useState(me.birth_date ?? '')
  const [height, setHeight] = useState(me.height_cm ?? 170)
  const [weight, setWeight] = useState(weightKg ? Number(weightKg) : 70)
  const [goal, setGoal] = useState<Goal | null>(me.goal)
  const [activity, setActivity] = useState<Activity | null>(me.activity_level)
  const [agreed, setAgreed] = useState(onboarded)

  // Первичная анкета обязательна, а при редактировании можно вернуться без сохранения
  const back = useCallback(() => navigate('/', { replace: true }), [navigate])
  useBackButton(onboarded ? back : null)

  const valid =
    sex !== null &&
    goal !== null &&
    activity !== null &&
    birthDate !== '' &&
    birthDate <= yearsAgo(MIN_AGE) &&
    birthDate >= yearsAgo(MAX_AGE) &&
    height >= 100 &&
    height <= 250 &&
    weight >= 30 &&
    weight <= 300 &&
    agreed

  const save = useMutation({
    mutationFn: putProfile,
    onSuccess: async () => {
      haptic.success()
      await queryClient.invalidateQueries({ queryKey: ['me'] })
      await queryClient.invalidateQueries({ queryKey: ['targets'] })
      navigate('/', { replace: true })
    },
    onError: () => haptic.error(),
  })

  const submit = useCallback(() => {
    if (!valid || save.isPending || !sex || !goal || !activity) return
    save.mutate({
      sex,
      birth_date: birthDate,
      height_cm: Math.round(height),
      weight_kg: Math.round(weight * 10) / 10,
      goal,
      activity_level: activity,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    })
  }, [valid, save, sex, birthDate, height, weight, goal, activity])

  useMainButton({
    text: onboarded ? 'Сохранить и пересчитать' : 'Рассчитать норму',
    onClick: submit,
    enabled: valid,
    loading: save.isPending,
  })

  return (
    <main className="p-4 pb-10">
      <h1 className="text-xl font-semibold">
        {onboarded ? 'Профиль и цели' : 'Расскажите о себе'}
      </h1>
      <p className="mt-1 text-sm text-hint">
        {onboarded
          ? 'Измените цель, активность или параметры — норма КБЖУ и воды пересчитается.'
          : 'По этим данным рассчитаем вашу норму калорий, белков, жиров и углеводов.'}
      </p>

      <Section title="Пол">
        <ChoiceGroup options={SEX_OPTIONS} value={sex} onChange={setSex} />
      </Section>

      <Section title="Дата рождения">
        <input
          type="date"
          value={birthDate}
          min={yearsAgo(MAX_AGE)}
          max={yearsAgo(MIN_AGE)}
          onChange={(e) => setBirthDate(e.target.value)}
          className="w-full rounded-2xl bg-bg-secondary p-4 text-lg outline-none"
        />
      </Section>

      <Section title="Параметры">
        <div className="grid gap-2">
          <SliderField
            label="Рост"
            unit="см"
            value={height}
            min={120}
            max={220}
            step={1}
            onChange={setHeight}
          />
          <SliderField
            label="Вес"
            unit="кг"
            value={weight}
            min={30}
            max={200}
            step={0.5}
            onChange={setWeight}
          />
        </div>
      </Section>

      <Section title="Цель">
        <ChoiceGroup options={GOAL_OPTIONS} value={goal} onChange={setGoal} columns={1} />
      </Section>

      <Section title="Активность">
        <ChoiceGroup
          options={ACTIVITY_OPTIONS}
          value={activity}
          onChange={setActivity}
          columns={1}
        />
      </Section>

      <label className="mt-6 flex items-start gap-3 rounded-2xl bg-bg-secondary p-4">
        <input
          type="checkbox"
          checked={agreed}
          onChange={(e) => setAgreed(e.target.checked)}
          className="mt-1 size-5 accent-button"
        />
        <span className="text-sm">
          Понимаю, что приложение носит информационный характер и не заменяет консультацию врача,
          диетолога или тренера.
        </span>
      </label>

      {save.isError && (
        <p className="mt-4 text-sm text-red-500">
          Не удалось сохранить. Проверьте данные и попробуйте ещё раз.
        </p>
      )}
    </main>
  )
}
