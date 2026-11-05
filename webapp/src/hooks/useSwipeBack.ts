import { useEffect } from 'react'

import { haptic } from '../lib/telegram'

// Жест «назад» как в Mini App BotFather (системный жест Android): экран стоит на месте,
// от левого края на высоте пальца выезжает капля со стрелкой. Выехала полностью и палец
// отпущен — возврат назад. Не дотянули — капля прячется.
const LOCK_DISTANCE = 12 // px: после этого решаем, жест горизонтальный или это прокрутка
const FULL_DISTANCE = 110 // px пальцем, за которые капля выезжает полностью
const BUBBLE_MAX = 44 // px: насколько капля выезжает из-за края
const TRIGGER = 0.9 // доля пути, после которой отпускание = «назад»
const HIDE_MS = 200

const CHEVRON =
  '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
  'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>'

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
    if (!onBack) return

    const bubble = document.createElement('div')
    bubble.className = 'swipe-back-bubble'
    bubble.innerHTML = CHEVRON
    bubble.style.display = 'none'
    document.body.appendChild(bubble)
    const chevron = bubble.firstElementChild as SVGElement

    let startX = 0
    let startY = 0
    let progress = 0 // 0…1 — насколько выехала капля
    let armed = false // капля выехала достаточно, отпускание = «назад»
    // idle — ждём касания, pending — ещё не ясно направление, swiping — тянем, ignored — не наш жест
    let state: 'idle' | 'pending' | 'swiping' | 'ignored' = 'idle'

    const draw = (y: number, ms: number) => {
      bubble.style.transition = ms ? `transform ${ms}ms ease-out` : 'none'
      bubble.style.transform = `translate3d(${progress * BUBBLE_MAX}px, ${y}px, 0)`
      chevron.style.transition = ms ? `opacity ${ms}ms, transform ${ms}ms` : 'none'
      chevron.style.opacity = String(Math.min(1, progress * 1.4))
      chevron.style.transform = `scale(${0.6 + progress * 0.4})`
    }

    const hide = (y: number) => {
      progress = 0
      draw(y, HIDE_MS)
      window.setTimeout(() => {
        if (state !== 'swiping') bubble.style.display = 'none'
      }, HIDE_MS)
    }

    const onStart = (e: TouchEvent) => {
      if (e.touches.length !== 1 || blocksSwipe(e.target)) {
        state = 'ignored'
        return
      }
      const t = e.touches[0]
      startX = t.clientX
      startY = t.clientY
      progress = 0
      armed = false
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
        startX = t.clientX // капля начинает выезжать с места, где жест распознан
        bubble.style.display = 'flex'
      }
      e.preventDefault() // не даём странице прокручиваться, пока тянем
      progress = Math.min(1, Math.max(0, t.clientX - startX) / FULL_DISTANCE)
      // Лёгкая отдача, когда капля «взвелась» и когда её потянули обратно
      const nowArmed = progress >= TRIGGER
      if (nowArmed !== armed) {
        armed = nowArmed
        haptic.select()
      }
      draw(t.clientY, 0)
    }

    const finish = (e: TouchEvent, allowBack: boolean) => {
      if (state !== 'swiping') {
        state = 'idle'
        return
      }
      state = 'idle'
      hide(e.changedTouches[0]?.clientY ?? startY)
      if (allowBack && armed) onBack()
    }
    const onEnd = (e: TouchEvent) => finish(e, true)
    const onCancel = (e: TouchEvent) => finish(e, false)

    document.addEventListener('touchstart', onStart, { passive: true })
    document.addEventListener('touchmove', onMove, { passive: false })
    document.addEventListener('touchend', onEnd)
    document.addEventListener('touchcancel', onCancel)
    return () => {
      document.removeEventListener('touchstart', onStart)
      document.removeEventListener('touchmove', onMove)
      document.removeEventListener('touchend', onEnd)
      document.removeEventListener('touchcancel', onCancel)
      bubble.remove()
    }
  }, [onBack])
}
