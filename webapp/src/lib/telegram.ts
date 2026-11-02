// Обёртка над window.Telegram.WebApp. Компоненты не трогают глобальный объект напрямую

interface TelegramWebApp {
  initData: string
  initDataUnsafe: { start_param?: string }
  colorScheme: 'light' | 'dark'
  ready(): void
  expand(): void
  HapticFeedback: {
    impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void
    notificationOccurred(type: 'error' | 'success' | 'warning'): void
  }
}

declare global {
  interface Window {
    Telegram?: { WebApp: TelegramWebApp }
  }
}

export const webApp: TelegramWebApp | undefined = window.Telegram?.WebApp

/** Открыто ли приложение внутри Telegram (есть подписанный initData). */
export const isInTelegram = Boolean(webApp?.initData)

export function initTelegram(): void {
  if (!webApp) return
  webApp.ready()
  webApp.expand()
}

export function getInitData(): string {
  return webApp?.initData ?? ''
}
