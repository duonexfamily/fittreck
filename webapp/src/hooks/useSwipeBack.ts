import { useEffect } from 'react'

import { haptic } from '../lib/telegram'

// Жест «назад»: свайп пальцем слева направо, экран едет за пальцем (как в iOS и Mini App BotFather)
const LOCK_DISTANCE = 10 // px: после этого решаем, жест горизонтальный или это прокрутка
const BACK_DISTANCE = 90 // px: протянули дальше — уходим назад
const BACK_VELOCITY = 0.5 // px/мс: быстрый короткий взмах тоже считается

/** Не перехватываем жест на слайдерах, полях ввода и в горизонтально прокручиваемых лентах. */
function blocksSwipe(target: EventTarget | null): boolean {
  let el = target instanceof Element ? target : null
  while (el && el !== document.body) {
    if (el.matches('input, textarea, select, [data-no-swipe]')) return true
    const { overflowX } = getComputedStyle(el)
    if ((overflowX === 'auto' || overflowX === 'scroll') && el.scrollWidth > el.clientWidth) {
      return true
    }
    el = el.parentElement
  }
  return false
}

export function useSwipeBack(onBack: (() => void) | null) {
  useEffect(() => {
    const root = document.getElementById('root')
    if (!root || !onBack) return

    let startX = 0
    let startY = 0
    let startTime = 0
    let dx = 0
    // idle — ждём касания, pending — ещё не ясно направление, swiping — тянем экран, ignored — не наш жест
    let state: 'idle' | 'pending' | 'swiping' | 'ignored' = 'idle'

    const setShift = (x: number, animate: boolean) => {
      root.style.transition = animate ? 'transform 180ms ease-out' : 'none'
      root.style.transform = x > 0 ? `translateX(${x}px)` : ''
    }

    const onStart = (e: TouchEvent) => {
      if (e.touches.length !== 1 || blocksSwipe(e.target)) {
        state = 'ignored'
        return
      }
      const t = e.touches[0]
      startX = t.clientX
      startY = t.clientY
      startTime = e.timeStamp
      dx = 0
      state = 'pending'
    }

    const onMove = (e: TouchEvent) => {
      if (state === 'idle' || state === 'ignored') return
      const t = e.touches[0]
      const moveX = t.clientX - startX
      const moveY = t.clientY - startY
      if (state === 'pending') {
        if (Math.abs(moveX) < LOCK_DISTANCE && Math.abs(moveY) < LOCK_DISTANCE) return
        // Вправо и заметно горизонтальнее, чем вертикально — иначе это обычная прокрутка
        state = moveX > 0 && moveX > Math.abs(moveY) * 1.5 ? 'swiping' : 'ignored'
        if (state === 'ignored') return
      }
      e.preventDefault() // не даём странице прокручиваться, пока тянем
      dx = Math.max(0, moveX)
      setShift(dx, false)
    }

    const onEnd = (e: TouchEvent) => {
      if (state === 'swiping') {
        const velocity = dx / Math.max(1, e.timeStamp - startTime)
        if (dx > BACK_DISTANCE || (dx > 40 && velocity > BACK_VELOCITY)) {
          haptic.select()
          setShift(0, false)
          onBack()
        } else {
          setShift(0, true)
        }
      }
      state = 'idle'
    }

    document.addEventListener('touchstart', onStart, { passive: true })
    document.addEventListener('touchmove', onMove, { passive: false })
    document.addEventListener('touchend', onEnd)
    document.addEventListener('touchcancel', onEnd)
    return () => {
      document.removeEventListener('touchstart', onStart)
      document.removeEventListener('touchmove', onMove)
      document.removeEventListener('touchend', onEnd)
      document.removeEventListener('touchcancel', onEnd)
      setShift(0, false)
    }
  }, [onBack])
}
