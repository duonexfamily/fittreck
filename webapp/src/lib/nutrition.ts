import type { MealType, Nutrients } from '../api/client'

export const MEAL_LABELS: Record<MealType, string> = {
  breakfast: 'Завтрак',
  lunch: 'Обед',
  dinner: 'Ужин',
  snack: 'Перекус',
}

export const MEAL_TYPES = Object.keys(MEAL_LABELS) as MealType[]

export function isMealType(value: string | null): value is MealType {
  return value !== null && value in MEAL_LABELS
}

/** КБЖУ порции по значениям на 100 г — для предпросмотра. Точный снимок считает backend. */
export function portion(per100g: Nutrients, grams: number): Nutrients {
  const k = grams / 100
  return {
    kcal: per100g.kcal * k,
    protein: per100g.protein * k,
    fat: per100g.fat * k,
    carbs: per100g.carbs * k,
  }
}

export const fmtKcal = (v: number) => String(Math.round(v))

export const fmtGrams = (v: number) => {
  const r = Math.round(v * 10) / 10
  return Number.isInteger(r) ? String(r) : r.toFixed(1).replace('.', ',')
}

/** Сегодняшняя дата YYYY-MM-DD в часовом поясе пользователя. */
export function todayIn(timeZone: string | undefined): string {
  // Локаль en-CA форматирует дату как YYYY-MM-DD
  return new Intl.DateTimeFormat('en-CA', { timeZone }).format(new Date())
}

export function shiftDate(date: string, days: number): string {
  const d = new Date(`${date}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

export function formatDay(date: string, today: string): string {
  if (date === today) return 'Сегодня'
  if (date === shiftDate(today, -1)) return 'Вчера'
  return new Date(`${date}T00:00:00Z`).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    weekday: 'short',
    timeZone: 'UTC',
  })
}
