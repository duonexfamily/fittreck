import { useEffect } from 'react'

import { webApp } from '../lib/telegram'

/** Нативная кнопка «Назад» в шапке Telegram. Скрывается при уходе со страницы. */
export function useBackButton(onClick: () => void) {
  useEffect(() => {
    const bb = webApp?.BackButton
    if (!bb) return
    bb.show()
    bb.onClick(onClick)
    return () => {
      bb.offClick(onClick)
      bb.hide()
    }
  }, [onClick])
}
