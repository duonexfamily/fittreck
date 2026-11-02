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

export interface Me {
  telegram_id: number
  first_name: string
  username: string | null
  timezone: string
  onboarded_at: string | null
}

export const getMe = () => api<Me>('/me')
