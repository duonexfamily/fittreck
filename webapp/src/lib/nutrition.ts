import type { MealType, Nutrients, QuickIn } from '../api/client'

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

export const QUICK_DEFAULT_NAME = 'Быстрая запись'

/** Число из поля ввода: запятая как точка, округление до десятых. Пустое поле — 0. */
export function parseDecimal(raw: string): number {
  const v = raw.trim() === '' ? 0 : Number(raw.replace(',', '.'))
  return Math.round(v * 10) / 10
}

/**
 * Быстрая запись из полей формы. Незаполненные БЖУ считаются нулём.
 * Границы совпадают с проверкой на backend (app/api/schemas/nutrition.py).
 */
export function parseQuick(name: string, raw: Record<keyof Nutrients, string>): QuickIn | null {
  const n: Nutrients = {
    kcal: parseDecimal(raw.kcal),
    protein: parseDecimal(raw.protein),
    fat: parseDecimal(raw.fat),
    carbs: parseDecimal(raw.carbs),
  }
  const values = Object.values(n)
  const valid =
    values.every((v) => Number.isFinite(v) && v >= 0) &&
    n.kcal <= 5000 &&
    n.protein <= 500 &&
    n.fat <= 500 &&
    n.carbs <= 500 &&
    values.some((v) => v > 0)
  return valid ? { name: name.trim() || QUICK_DEFAULT_NAME, ...n } : null
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
