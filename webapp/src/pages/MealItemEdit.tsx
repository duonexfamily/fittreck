import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { Navigate, useLocation, useNavigate, useParams, useSearchParams } from 'react-router'

import { type MealItem, deleteMealItem, updateMealItem, updateQuickItem } from '../api/client'
import NutrientsRow from '../components/NutrientsRow'
import QuickFields, { type QuickRaw } from '../components/QuickFields'
import SliderField from '../components/SliderField'
import { useBackButton } from '../hooks/useBackButton'
import { useMainButton } from '../hooks/useMainButton'
import { fmtGrams, parseQuick } from '../lib/nutrition'
import { haptic } from '../lib/telegram'

type Done = () => Promise<void>

function GramsEdit({ item, grams0, onDone }: { item: MealItem; grams0: number; onDone: Done }) {
  const [grams, setGrams] = useState(grams0)
  const save = useMutation({
    mutationFn: () => updateMealItem(item.id, Math.round(grams * 10) / 10),
    onSuccess: onDone,
    onError: () => haptic.error(),
  })

  const valid = grams > 0 && grams <= 5000 && grams !== grams0
  const submit = useCallback(() => {
    if (valid && !save.isPending) save.mutate()
  }, [valid, save])
  useMainButton({ text: 'Сохранить', onClick: submit, enabled: valid, loading: save.isPending })

  // Пересчёт из снимка записи — так же, как на backend
  const k = grams / grams0
  const preview = {
    kcal: item.kcal * k,
    protein: item.protein * k,
    fat: item.fat * k,
    carbs: item.carbs * k,
  }

  return (
    <>
      <h1 className="page-title">{item.name}</h1>
      <p className="mt-1 text-sm text-hint">Сейчас в дневнике: {fmtGrams(grams0)} г</p>
      <div className="mt-4">
        <SliderField
          label="Порция"
          unit="г"
          value={grams}
          min={5}
          max={1000}
          step={5}
          onChange={setGrams}
        />
      </div>
      <div className="mt-3">
        <NutrientsRow n={preview} />
      </div>
      {save.isError && <p className="mt-4 text-sm text-destructive">Не получилось сохранить.</p>}
    </>
  )
}

function QuickEdit({ item, onDone }: { item: MealItem; onDone: Done }) {
  const [name, setName] = useState(item.name)
  const [raw, setRaw] = useState<QuickRaw>({
    kcal: String(item.kcal),
    protein: String(item.protein),
    fat: String(item.fat),
    carbs: String(item.carbs),
  })
  const quick = parseQuick(name, raw)
  const save = useMutation({
    mutationFn: updateQuickItem.bind(null, item.id),
    onSuccess: onDone,
    onError: () => haptic.error(),
  })

  const submit = useCallback(() => {
    if (quick && !save.isPending) save.mutate(quick)
  }, [quick, save])
  useMainButton({
    text: 'Сохранить',
    onClick: submit,
    enabled: Boolean(quick),
    loading: save.isPending,
  })

  return (
    <>
      <h1 className="page-title">Быстрая запись</h1>
      <p className="mt-1 text-sm text-hint">КБЖУ всей порции.</p>
      <QuickFields name={name} onName={setName} raw={raw} onRaw={setRaw} />
      {save.isError && <p className="mt-4 text-sm text-destructive">Не получилось сохранить.</p>}
    </>
  )
}

export default function MealItemEdit() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { id } = useParams()
  const [params] = useSearchParams()
  const date = params.get('date') ?? ''
  // Запись передаётся из дневника. После перезагрузки страницы её нет — возвращаемся в дневник
  const item = (useLocation().state as { item?: MealItem } | null)?.item

  const toDiary = useCallback(
    () => navigate(date ? `/nutrition?date=${date}` : '/nutrition', { replace: true }),
    [navigate, date],
  )
  useBackButton(toDiary)

  const onDone = async () => {
    haptic.success()
    await queryClient.invalidateQueries({ queryKey: ['diary'] })
    toDiary()
  }
  const remove = useMutation({
    mutationFn: () => deleteMealItem(Number(id)),
    onSuccess: onDone,
    onError: () => haptic.error(),
  })

  if (!item || String(item.id) !== id) return <Navigate to="/nutrition" replace />

  return (
    <main className="p-4 pb-10">
      {item.grams === null ? (
        <QuickEdit item={item} onDone={onDone} />
      ) : (
        <GramsEdit item={item} grams0={item.grams} onDone={onDone} />
      )}
      <button
        type="button"
        disabled={remove.isPending}
        onClick={() => remove.mutate()}
        className="mt-6 w-full rounded-2xl bg-bg-secondary p-4 font-medium text-destructive disabled:opacity-50"
      >
        Удалить из дневника
      </button>
      {remove.isError && <p className="mt-4 text-sm text-destructive">Не получилось удалить.</p>}
    </main>
  )
}
