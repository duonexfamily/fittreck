import { getInitData } from '../lib/telegram'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

/** Запрос к нашему API. Каждый запрос подписан initData Telegram. */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `tma ${getInitData()}`,
      ...init.headers,
    },
  })
  if (!response.ok) {
    throw new ApiError(response.status, `API ${response.status}`)
  }
  // 204 No Content — тела нет
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export type Sex = 'male' | 'female'
export type Goal = 'lose' | 'maintain' | 'gain'
export type Activity = 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active'

export interface Me {
  telegram_id: number
  first_name: string
  username: string | null
  sex: Sex | null
  birth_date: string | null
  height_cm: number | null
  goal: Goal | null
  activity_level: Activity | null
  timezone: string
  onboarded_at: string | null
}

export interface ProfileIn {
  sex: Sex
  birth_date: string
  height_cm: number
  weight_kg: number
  goal: Goal
  activity_level: Activity
  timezone: string
}

export interface Targets {
  weight_kg: string
  bmr: number
  tdee: number
  kcal: number
  protein_g: number
  fat_g: number
  carbs_g: number
}

export const getMe = () => api<Me>('/me')

export const putProfile = (body: ProfileIn) =>
  api<Me>('/me/profile', { method: 'PUT', body: JSON.stringify(body) })

export const getTargets = () => api<Targets>('/me/targets')

export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack'

/** КБЖУ: у продукта — на 100 г, у записи дневника — на порцию. */
export interface Nutrients {
  kcal: number
  protein: number
  fat: number
  carbs: number
}

export interface Food extends Nutrients {
  id: number
  name: string
  own: boolean
  favorite: boolean
}

export type FoodIn = Omit<Food, 'id' | 'own' | 'favorite'>

/** Быстрая запись: КБЖУ порции вручную, без продукта. */
export interface QuickIn extends Nutrients {
  name: string
}

export interface MealItem extends Nutrients {
  id: number
  food_id: number | null
  name: string
  // null — быстрая запись без граммовки
  grams: number | null
}

export interface Meal {
  meal_type: MealType
  items: MealItem[]
  total: Nutrients
}

export interface Diary {
  date: string
  meals: Meal[]
  total: Nutrients
}

export const searchFoods = (query: string) =>
  api<Food[]>(`/foods?query=${encodeURIComponent(query)}`)

export const getFavoriteFoods = () => api<Food[]>('/foods/favorites')

export const setFavorite = (id: number, favorite: boolean) =>
  api<void>(`/foods/${id}/favorite`, { method: favorite ? 'PUT' : 'DELETE' })

export const createFood = (body: FoodIn) =>
  api<Food>('/foods', { method: 'POST', body: JSON.stringify(body) })

export const getDiary = (date: string) => api<Diary>(`/meals?date=${date}`)

export const addMealItem = (
  meal: MealType,
  body: { date: string; food_id: number; grams: number },
) => api<MealItem>(`/meals/${meal}/items`, { method: 'POST', body: JSON.stringify(body) })

export const addQuickItem = (meal: MealType, body: QuickIn & { date: string }) =>
  api<MealItem>(`/meals/${meal}/quick-items`, { method: 'POST', body: JSON.stringify(body) })

export const updateMealItem = (id: number, grams: number) =>
  api<MealItem>(`/meal-items/${id}`, { method: 'PATCH', body: JSON.stringify({ grams }) })

export const updateQuickItem = (id: number, quick: QuickIn) =>
  api<MealItem>(`/meal-items/${id}`, { method: 'PATCH', body: JSON.stringify({ quick }) })

export const deleteMealItem = (id: number) => api<void>(`/meal-items/${id}`, { method: 'DELETE' })

export interface WeightEntry {
  date: string
  weight_kg: number
}

export interface WaterDay {
  date: string
  ml: number
  target_ml: number
}

export const getWeightHistory = () => api<WeightEntry[]>('/weight')

export const putWeight = (body: { date: string; weight_kg: number }) =>
  api<WeightEntry>('/weight', { method: 'PUT', body: JSON.stringify(body) })

export const deleteWeight = (date: string) => api<void>(`/weight/${date}`, { method: 'DELETE' })

export const getWater = (date: string) => api<WaterDay>(`/water?date=${date}`)

export const addWater = (body: { date: string; delta_ml: number }) =>
  api<WaterDay>('/water', { method: 'POST', body: JSON.stringify(body) })
