import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'

import {
  type Food,
  type MealType,
  type Nutrients,
  addMealItem,
  addQuickItem,
  createFood,
  getFavoriteFoods,
  getMe,
  searchFoods,
  setFavorite,
} from '../api/client'
import ChoiceGroup from '../components/ChoiceGroup'
import NumberInput from '../components/NumberInput'
import NutrientsRow from '../components/NutrientsRow'
import QuickFields, { type QuickRaw } from '../components/QuickFields'
import SliderField from '../components/SliderField'
import { useBackButton } from '../hooks/useBackButton'
import { useDebounced } from '../hooks/useDebounced'
import { useMainButton } from '../hooks/useMainButton'
import {
  MEAL_LABELS,
  MEAL_TYPES,
  fmtKcal,
  isMealType,
  parseQuick,
  portion,
  todayIn,
} from '../lib/nutrition'
import { haptic } from '../lib/telegram'

const MEAL_OPTIONS = MEAL_TYPES.map((value) => ({ value, label: MEAL_LABELS[value] }))

function FoodList({ foods, onSelect }: { foods: Food[]; onSelect: (f: Food) => void }) {
  return (
    <ul className="mt-2 divide-y divide-bg-secondary">
      {foods.map((f) => (
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
              {f.favorite && <span className="mr-1">⭐</span>}
              {f.name}
              {f.own && <span className="ml-2 text-xs text-hint">свой</span>}
            </span>
            <span className="shrink-0 text-sm text-hint">{fmtKcal(f.kcal)} ккал/100 г</span>
          </button>
        </li>
      ))}
    </ul>
  )
}

function FoodSearch({
  onSelect,
  onCreate,
  onQuick,
}: {
  onSelect: (f: Food) => void
  onCreate: () => void
  onQuick: () => void
}) {
  const [query, setQuery] = useState('')
  const q = useDebounced(query.trim(), 300)
  const foods = useQuery({
    queryKey: ['foods', q],
    queryFn: () => searchFoods(q),
    placeholderData: (prev) => prev,
  })
  const favorites = useQuery({ queryKey: ['foods', 'favorites'], queryFn: getFavoriteFoods })
  // Избранное показано отдельным списком — в недавних не повторяем
  const favoriteIds = new Set(favorites.data?.map((f) => f.id))
  const recent = foods.data?.filter((f) => !favoriteIds.has(f.id)) ?? []

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
      {q ? (
        <>
          {foods.data?.length === 0 && (
            <p className="mt-4 text-hint">Ничего не нашлось. Добавьте свой продукт.</p>
          )}
          {foods.data && <FoodList foods={foods.data} onSelect={onSelect} />}
        </>
      ) : (
        <>
          {favorites.data && favorites.data.length > 0 && (
            <>
              <h2 className="mt-4 mb-1 text-sm font-medium text-hint">Избранное</h2>
              <FoodList foods={favorites.data} onSelect={onSelect} />
            </>
          )}
          {recent.length > 0 && (
            <>
              <h2 className="mt-4 mb-1 text-sm font-medium text-hint">Недавние</h2>
              <FoodList foods={recent} onSelect={onSelect} />
            </>
          )}
        </>
      )}
      {foods.isError && <p className="mt-4 text-hint">Не удалось выполнить поиск.</p>}
      <div className="mt-4 grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={onQuick}
          className="rounded-2xl bg-bg-secondary p-4 text-left font-medium text-link"
        >
          + Быстрая запись
        </button>
        <button
          type="button"
          onClick={onCreate}
          className="rounded-2xl bg-bg-secondary p-4 text-left font-medium text-link"
        >
          + Свой продукт
        </button>
      </div>
    </>
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
        <p className="mt-4 text-sm text-destructive">Не удалось сохранить. Проверьте значения.</p>
      )}
    </>
  )
}

function QuickForm({ meal, date }: { meal: MealType; date: string }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [raw, setRaw] = useState<QuickRaw>({ kcal: '', protein: '', fat: '', carbs: '' })
  const [mealType, setMealType] = useState<MealType>(meal)
  const quick = parseQuick(name, raw)

  const save = useMutation({
    mutationFn: (v: { meal: MealType; body: Parameters<typeof addQuickItem>[1] }) =>
      addQuickItem(v.meal, v.body),
    onSuccess: async () => {
      haptic.success()
      await queryClient.invalidateQueries({ queryKey: ['diary', date] })
      navigate(`/nutrition?date=${date}`, { replace: true })
    },
    onError: () => haptic.error(),
  })

  const submit = useCallback(() => {
    if (quick && !save.isPending) save.mutate({ meal: mealType, body: { date, ...quick } })
  }, [quick, save, mealType, date])

  useMainButton({
    text: 'Добавить',
    onClick: submit,
    enabled: Boolean(quick),
    loading: save.isPending,
  })

  return (
    <>
      <h1 className="text-xl font-semibold">Быстрая запись</h1>
      <p className="mt-1 text-sm text-hint">
        КБЖУ всей порции — например, из меню кафе. Название можно не писать.
      </p>
      <QuickFields name={name} onName={setName} raw={raw} onRaw={setRaw} />
      <h2 className="mt-6 mb-2 text-sm font-medium text-hint">Приём пищи</h2>
      <ChoiceGroup options={MEAL_OPTIONS} value={mealType} onChange={setMealType} />
      {save.isError && <p className="mt-4 text-sm text-destructive">Не удалось добавить запись.</p>}
    </>
  )
}

function FavoriteButton({ food }: { food: Food }) {
  const queryClient = useQueryClient()
  // Выбранный продукт пришёл из списка и сам не обновится — храним отметку локально
  const [on, setOn] = useState(food.favorite)
  const toggle = useMutation({
    mutationFn: (next: boolean) => setFavorite(food.id, next),
    onMutate: (next) => {
      haptic.select()
      setOn(next)
    },
    onError: (_e, next) => {
      haptic.error()
      setOn(!next)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['foods'] }),
  })
  return (
    <button
      type="button"
      disabled={toggle.isPending}
      onClick={() => toggle.mutate(!on)}
      aria-pressed={on}
      className="shrink-0 rounded-full bg-bg-secondary px-3 py-1 text-sm"
    >
      {on ? '⭐ В избранном' : '☆ В избранное'}
    </button>
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
      <div className="flex items-start justify-between gap-3">
        <h1 className="text-xl font-semibold">{food.name}</h1>
        <FavoriteButton food={food} />
      </div>
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
      {save.isError && <p className="mt-4 text-sm text-destructive">Не удалось добавить продукт.</p>}
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
  const [mode, setMode] = useState<'search' | 'create' | 'quick'>('search')

  // «Назад» возвращает на шаг назад внутри экрана, а с поиска — в дневник
  const back = useCallback(() => {
    if (selected) setSelected(null)
    else if (mode !== 'search') setMode('search')
    else navigate(`/nutrition?date=${date}`, { replace: true })
  }, [selected, mode, navigate, date])
  useBackButton(back)

  return (
    <main className="p-4 pb-10">
      {selected ? (
        <PortionForm food={selected} meal={meal} date={date} />
      ) : mode === 'create' ? (
        <FoodCreate
          onCreated={(f) => {
            setMode('search')
            setSelected(f)
          }}
        />
      ) : mode === 'quick' ? (
        <QuickForm meal={meal} date={date} />
      ) : (
        <FoodSearch
          onSelect={setSelected}
          onCreate={() => setMode('create')}
          onQuick={() => setMode('quick')}
        />
      )}
    </main>
  )
}
