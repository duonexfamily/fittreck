import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'

import {
  type Food,
  type MealType,
  type Nutrients,
  addMealItem,
  createFood,
  getMe,
  searchFoods,
} from '../api/client'
import ChoiceGroup from '../components/ChoiceGroup'
import NutrientsRow from '../components/NutrientsRow'
import SliderField from '../components/SliderField'
import { useBackButton } from '../hooks/useBackButton'
import { useMainButton } from '../hooks/useMainButton'
import { MEAL_LABELS, MEAL_TYPES, fmtKcal, isMealType, portion, todayIn } from '../lib/nutrition'
import { haptic } from '../lib/telegram'

const MEAL_OPTIONS = MEAL_TYPES.map((value) => ({ value, label: MEAL_LABELS[value] }))

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return debounced
}

function FoodSearch({ onSelect, onCreate }: { onSelect: (f: Food) => void; onCreate: () => void }) {
  const [query, setQuery] = useState('')
  const q = useDebounced(query.trim(), 300)
  const foods = useQuery({
    queryKey: ['foods', q],
    queryFn: () => searchFoods(q),
    placeholderData: (prev) => prev,
  })

  return (
    <>
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Найти продукт"
        maxLength={64}
        autoFocus
        className="w-full rounded-2xl bg-bg-secondary p-4 text-lg outline-none"
      />
      {!q && foods.data && foods.data.length > 0 && (
        <h2 className="mt-4 mb-1 text-sm font-medium text-hint">Недавние</h2>
      )}
      {q && foods.data?.length === 0 && (
        <p className="mt-4 text-hint">Ничего не нашлось. Добавьте свой продукт.</p>
      )}
      {foods.isError && <p className="mt-4 text-hint">Не удалось выполнить поиск.</p>}
      <ul className="mt-2 divide-y divide-bg-secondary">
        {foods.data?.map((f) => (
          <li key={f.id}>
            <button
              type="button"
              onClick={() => {
                haptic.select()
                onSelect(f)
              }}
              className="flex w-full items-baseline justify-between gap-3 py-3 text-left"
            >
              <span className="min-w-0 truncate">
                {f.name}
                {f.own && <span className="ml-2 text-xs text-hint">свой</span>}
              </span>
              <span className="shrink-0 text-sm text-hint">{fmtKcal(f.kcal)} ккал/100 г</span>
            </button>
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={onCreate}
        className="mt-4 w-full rounded-2xl bg-bg-secondary p-4 text-left font-medium text-link"
      >
        + Свой продукт
      </button>
    </>
  )
}

function NumberInput({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (v: string) => void
}) {
  return (
    <label className="flex items-baseline justify-between rounded-2xl bg-bg-secondary p-4">
      <span className="text-hint">{label}</span>
      <input
        type="number"
        inputMode="decimal"
        min={0}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-24 bg-transparent text-right text-lg font-semibold outline-none"
      />
    </label>
  )
}

// Границы совпадают с проверкой на backend (app/api/schemas/nutrition.py)
function parseFood(name: string, raw: Record<keyof Nutrients, string>) {
  const n = Object.fromEntries(
    Object.entries(raw).map(([k, v]) => [k, Math.round(Number(v.replace(',', '.')) * 10) / 10]),
  ) as unknown as Nutrients
  const valid =
    name.trim().length > 0 &&
    Object.values(raw).every((v) => v.trim() !== '') &&
    Object.values(n).every((v) => Number.isFinite(v) && v >= 0) &&
    n.kcal <= 900 &&
    n.protein + n.fat + n.carbs <= 100
  return valid ? { name: name.trim(), ...n } : null
}

function FoodCreate({ onCreated }: { onCreated: (f: Food) => void }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [raw, setRaw] = useState({ kcal: '', protein: '', fat: '', carbs: '' })
  const food = parseFood(name, raw)
  const set = (key: keyof Nutrients) => (v: string) => setRaw((r) => ({ ...r, [key]: v }))

  const save = useMutation({
    mutationFn: createFood,
    onSuccess: async (created) => {
      haptic.success()
      await queryClient.invalidateQueries({ queryKey: ['foods'] })
      onCreated(created)
    },
    onError: () => haptic.error(),
  })

  const submit = useCallback(() => {
    if (food && !save.isPending) save.mutate(food)
  }, [food, save])

  useMainButton({
    text: 'Сохранить продукт',
    onClick: submit,
    enabled: Boolean(food),
    loading: save.isPending,
  })

  return (
    <>
      <h1 className="text-xl font-semibold">Свой продукт</h1>
      <p className="mt-1 text-sm text-hint">Значения на 100 г — их можно найти на упаковке.</p>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Название"
        maxLength={128}
        autoFocus
        className="mt-4 w-full rounded-2xl bg-bg-secondary p-4 text-lg outline-none"
      />
      <div className="mt-2 grid gap-2">
        <NumberInput label="Калории, ккал" value={raw.kcal} onChange={set('kcal')} />
        <NumberInput label="Белки, г" value={raw.protein} onChange={set('protein')} />
        <NumberInput label="Жиры, г" value={raw.fat} onChange={set('fat')} />
        <NumberInput label="Углеводы, г" value={raw.carbs} onChange={set('carbs')} />
      </div>
      {save.isError && (
        <p className="mt-4 text-sm text-red-500">Не удалось сохранить. Проверьте значения.</p>
      )}
    </>
  )
}

function PortionForm({ food, meal, date }: { food: Food; meal: MealType; date: string }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [grams, setGrams] = useState(100)
  const [mealType, setMealType] = useState<MealType>(meal)
  const valid = grams > 0 && grams <= 5000

  const save = useMutation({
    mutationFn: () =>
      addMealItem(mealType, { date, food_id: food.id, grams: Math.round(grams * 10) / 10 }),
    onSuccess: async () => {
      haptic.success()
      await queryClient.invalidateQueries({ queryKey: ['diary', date] })
      navigate(`/nutrition?date=${date}`, { replace: true })
    },
    onError: () => haptic.error(),
  })

  const submit = useCallback(() => {
    if (valid && !save.isPending) save.mutate()
  }, [valid, save])

  useMainButton({ text: 'Добавить', onClick: submit, enabled: valid, loading: save.isPending })

  return (
    <>
      <h1 className="text-xl font-semibold">{food.name}</h1>
      <p className="mt-1 text-sm text-hint">{fmtKcal(food.kcal)} ккал на 100 г</p>
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
        <NutrientsRow n={portion(food, grams)} />
      </div>
      <h2 className="mt-6 mb-2 text-sm font-medium text-hint">Приём пищи</h2>
      <ChoiceGroup options={MEAL_OPTIONS} value={mealType} onChange={setMealType} />
      {save.isError && <p className="mt-4 text-sm text-red-500">Не удалось добавить продукт.</p>}
    </>
  )
}

export default function NutritionAdd() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const me = useQuery({ queryKey: ['me'], queryFn: getMe })
  const mealParam = params.get('meal')
  const meal: MealType = isMealType(mealParam) ? mealParam : 'snack'
  const date = params.get('date') ?? todayIn(me.data?.timezone)

  const [selected, setSelected] = useState<Food | null>(null)
  const [creating, setCreating] = useState(false)

  // «Назад» возвращает на шаг назад внутри экрана, а с поиска — в дневник
  const back = useCallback(() => {
    if (selected) setSelected(null)
    else if (creating) setCreating(false)
    else navigate(`/nutrition?date=${date}`, { replace: true })
  }, [selected, creating, navigate, date])
  useBackButton(back)

  return (
    <main className="p-4 pb-10">
      {selected ? (
        <PortionForm food={selected} meal={meal} date={date} />
      ) : creating ? (
        <FoodCreate
          onCreated={(f) => {
            setCreating(false)
            setSelected(f)
          }}
        />
      ) : (
        <FoodSearch onSelect={setSelected} onCreate={() => setCreating(true)} />
      )}
    </main>
  )
}
