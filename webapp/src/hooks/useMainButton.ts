import { useEffect } from 'react'

import { webApp } from '../lib/telegram'

interface Options {
  text: string
  onClick: () => void
  enabled?: boolean
  loading?: boolean
}

/** Нативная кнопка Telegram внизу экрана. Скрывается при уходе со страницы. */
export function useMainButton({ text, onClick, enabled = true, loading = false }: Options) {
  useEffect(() => {
    if (!webApp) return
    const mb = webApp.MainButton
    const theme = webApp.themeParams
    mb.setParams({
      text,
      is_visible: true,
      is_active: enabled && !loading,
      // Неактивная кнопка — цветом подсказок, чтобы было видно, что нажать нельзя
      color: enabled ? theme.button_color : theme.hint_color,
    })
    if (loading) mb.showProgress(false)
    else mb.hideProgress()
  }, [text, enabled, loading])

  useEffect(() => {
    const mb = webApp?.MainButton
    if (!mb) return
    mb.onClick(onClick)
    return () => mb.offClick(onClick)
  }, [onClick])

  useEffect(() => () => webApp?.MainButton.hide(), [])
}
