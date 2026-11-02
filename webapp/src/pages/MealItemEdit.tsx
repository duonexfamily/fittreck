import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { Navigate, useLocation, useNavigate, useParams, useSearchParams } from 'react-router'

import { type MealItem, deleteMealItem, updateMealItem } from '../api/client'
import NutrientsRow from '../components/NutrientsRow'
import SliderField from '../components/SliderField'
import { useBackButton } from '../hooks/useBackButton'
import { useMainButton } from '../hooks/useMainButton'
import { fmtGrams } from '../lib/nutrition'
import { haptic } from '../lib/telegram'

export default function MealItemEdit() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { id } = useParams()
  const [params] = useSearchParams()
  const date = params.get('date') ?? ''
  // Запись передаётся из дневника. После перезагрузки страницы её нет — возвращаемся в дневник
  const item = (useLocation().state as { item?: MealItem } | null)?.item
  const [grams, setGrams] = useState(item?.grams ?? 100)

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
  const save = useMutation({
    mutationFn: () => updateMealItem(Number(id), Math.round(grams * 10) / 10),
    onSuccess: onDone,
    onError: () => haptic.error(),
  })
  const remove = useMutation({
    mutationFn: () => deleteMealItem(Number(id)),
    onSuccess: onDone,
    onError: () => haptic.error(),
  })

  const valid = grams > 0 && grams <= 5000 && grams !== item?.grams
  const busy = save.isPending || remove.isPending
  const submit = useCallback(() => {
    if (valid && !busy) save.mutate()
  }, [valid, busy, save])
  useMainButton({ text: 'Сохранить', onClick: submit, enabled: valid, loading: save.isPending })

  if (!item || String(item.id) !== id) return <Navigate to="/nutrition" replace />

  // Пересчёт из снимка записи — так же, как на backend
  const k = grams / item.grams
  const preview = {
    kcal: item.kcal * k,
    protein: item.protein * k,
    fat: item.fat * k,
    carbs: item.carbs * k,
  }

  return (
    <main className="p-4 pb-10">
      <h1 className="text-xl font-semibold">{item.name}</h1>
      <p className="mt-1 text-sm text-hint">Сейчас в дневнике: {fmtGrams(item.grams)} г</p>
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
      <button
        type="button"
        disabled={busy}
        onClick={() => remove.mutate()}
        className="mt-6 w-full rounded-2xl bg-bg-secondary p-4 font-medium text-red-500 disabled:opacity-50"
      >
        Удалить из дневника
      </button>
      {(save.isError || remove.isError) && (
        <p className="mt-4 text-sm text-red-500">Не получилось. Попробуйте ещё раз.</p>
      )}
    </main>
  )
}
