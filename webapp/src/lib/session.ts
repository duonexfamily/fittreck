import { useSyncExternalStore } from 'react'

// initData действует 24 часа. Любой ответ 401 — сессия устарела, помогает только новый запуск из бота
let expired = false
const listeners = new Set<() => void>()

export function markSessionExpired(): void {
  if (expired) return
  expired = true
  listeners.forEach((notify) => notify())
}

export function useSessionExpired(): boolean {
  return useSyncExternalStore(
    (notify) => {
      listeners.add(notify)
      return () => listeners.delete(notify)
    },
    () => expired,
  )
}
