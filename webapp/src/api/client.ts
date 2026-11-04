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

export type MuscleGroup = 'chest' | 'back' | 'shoulders' | 'arms' | 'legs' | 'core' | 'full_body'
/** strength — повторения × вес, cardio — время и дистанция, stretch — на время. */
export type ExerciseKind = 'strength' | 'cardio' | 'stretch'
/** planned — не завершена, done — выполнена. */
export type WorkoutStatus = 'planned' | 'done'

export interface Exercise {
  id: number
  name: string
  muscle_group: MuscleGroup
  kind: ExerciseKind
  own: boolean
}

export type ExerciseIn = Omit<Exercise, 'id' | 'own'>

/** Значения подхода. Заполнены поля, подходящие виду упражнения. */
export interface SetValues {
  reps: number | null
  weight_kg: number | null
  duration_s: number | null
  distance_m: number | null
}

export interface WorkoutSet extends SetValues {
  id: number
  exercise_id: number
  set_no: number
  // false — подход из шаблона, ещё не выполнен
  done: boolean
}

export interface Workout {
  id: number
  date: string
  status: WorkoutStatus
  started_at: string | null
  finished_at: string | null
  rpe: number | null
  note: string | null
  exercises: { exercise: Exercise; sets: WorkoutSet[] }[]
  volume_kg: number
}

/** set_count и volume_kg — только по выполненным подходам. */
export interface WorkoutSummary {
  id: number
  date: string
  status: WorkoutStatus
  rpe: number | null
  exercise_names: string[]
  set_count: number
  volume_kg: number
}

/** Передаются только меняемые поля. rpe/note = null — очистить. */
export type WorkoutPatch = Partial<Pick<Workout, 'status' | 'rpe' | 'note'>>

export const searchExercises = (p: {
  query: string
  muscle?: MuscleGroup
  kind?: ExerciseKind
}) => {
  const params = new URLSearchParams({ query: p.query })
  if (p.muscle) params.set('muscle', p.muscle)
  if (p.kind) params.set('kind', p.kind)
  return api<Exercise[]>(`/exercises?${params}`)
}

export const createExercise = (body: ExerciseIn) =>
  api<Exercise>('/exercises', { method: 'POST', body: JSON.stringify(body) })

export const getWorkouts = (from: string, to: string) =>
  api<WorkoutSummary[]>(`/workouts?from=${from}&to=${to}`)

export const createWorkout = (date: string) =>
  api<Workout>('/workouts', { method: 'POST', body: JSON.stringify({ date }) })

export const getWorkout = (id: number) => api<Workout>(`/workouts/${id}`)

export const updateWorkout = (id: number, body: WorkoutPatch) =>
  api<Workout>(`/workouts/${id}`, { method: 'PATCH', body: JSON.stringify(body) })

export const deleteWorkout = (id: number) => api<void>(`/workouts/${id}`, { method: 'DELETE' })

export const addSet = (workoutId: number, body: SetValues & { exercise_id: number }) =>
  api<WorkoutSet>(`/workouts/${workoutId}/sets`, { method: 'POST', body: JSON.stringify(body) })

/** Значения подхода заменяются целиком. Сохранённый подход — выполнен, если не указано иное. */
export const updateSet = (id: number, body: SetValues & { done?: boolean }) =>
  api<WorkoutSet>(`/workout-sets/${id}`, { method: 'PATCH', body: JSON.stringify(body) })

export const deleteSet = (id: number) => api<void>(`/workout-sets/${id}`, { method: 'DELETE' })

export interface Template {
  id: number
  name: string
  exercise_names: string[]
  set_count: number
}

export const getTemplates = () => api<Template[]>('/templates')

/** Шаблон из тренировки: её упражнения и подходы. */
export const createTemplate = (body: { name: string; workout_id: number }) =>
  api<Template>('/templates', { method: 'POST', body: JSON.stringify(body) })

export const deleteTemplate = (id: number) => api<void>(`/templates/${id}`, { method: 'DELETE' })

/** Тренировка по шаблону на дату: подходы скопированы невыполненными. */
export const startTemplate = (id: number, date: string) =>
  api<Workout>(`/templates/${id}/start`, { method: 'POST', body: JSON.stringify({ date }) })

/** Оценки 1–5. Время — на часах пользователя, HH:MM:SS. */
export interface CheckinValues {
  bed_time: string | null
  wake_time: string | null
  sleep_quality: number | null
  energy: number | null
  stress: number | null
  mood: number | null
  note: string | null
}

export interface Checkin extends CheckinValues {
  date: string
  // По времени отхода ко сну и подъёма
  sleep_minutes: number | null
}

export const getCheckins = (from: string, to: string) =>
  api<Checkin[]>(`/checkins?from=${from}&to=${to}`)

/** Чек-ин за день заменяется целиком. */
export const putCheckin = (date: string, body: CheckinValues) =>
  api<Checkin>(`/checkins/${date}`, { method: 'PUT', body: JSON.stringify(body) })
