import { useEffect } from 'react'

import { webApp } from '../lib/telegram'
import { useSwipeBack } from './useSwipeBack'

/**
 * Нативная кнопка «Назад» в шапке Telegram и свайп вправо для возврата.
 * Скрывается при уходе со страницы. null — не показывать.
 */
export function useBackButton(onClick: (() => void) | null) {
  useSwipeBack(onClick)
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
