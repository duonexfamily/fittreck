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
