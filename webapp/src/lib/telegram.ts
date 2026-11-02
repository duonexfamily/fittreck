// Обёртка над window.Telegram.WebApp. Компоненты не трогают глобальный объект напрямую

interface MainButton {
  setParams(params: { text?: string; color?: string; is_active?: boolean; is_visible?: boolean }): void
  show(): void
  hide(): void
  showProgress(leaveActive?: boolean): void
  hideProgress(): void
  onClick(cb: () => void): void
  offClick(cb: () => void): void
}

interface TelegramWebApp {
  initData: string
  initDataUnsafe: { start_param?: string }
  colorScheme: 'light' | 'dark'
  themeParams: { button_color?: string; hint_color?: string }
  MainButton: MainButton
  ready(): void
  expand(): void
  HapticFeedback: {
    impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void
    notificationOccurred(type: 'error' | 'success' | 'warning'): void
    selectionChanged(): void
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

export const haptic = {
  select: () => webApp?.HapticFeedback.selectionChanged(),
  success: () => webApp?.HapticFeedback.notificationOccurred('success'),
  error: () => webApp?.HapticFeedback.notificationOccurred('error'),
}
