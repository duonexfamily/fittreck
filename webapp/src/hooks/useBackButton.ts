import { useEffect } from 'react'

import { webApp } from '../lib/telegram'

/** Нативная кнопка «Назад» в шапке Telegram. Скрывается при уходе со страницы. null — не показывать. */
export function useBackButton(onClick: (() => void) | null) {
  useEffect(() => {
    const bb = webApp?.BackButton
    if (!bb || !onClick) return
    bb.show()
    bb.onClick(onClick)
    return () => {
      bb.offClick(onClick)
      bb.hide()
    }
  }, [onClick])
}
