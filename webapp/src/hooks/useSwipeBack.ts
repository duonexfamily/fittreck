import { useEffect } from 'react'

import { haptic } from '../lib/telegram'

// Жест «назад» как в iOS и Mini App BotFather: экран едет за пальцем, под ним затемнённый фон.
// Отпустили дальше трети экрана или смахнули — экран плавно уезжает вправо, предыдущий выезжает слева.
const LOCK_DISTANCE = 12 // px: после этого решаем, жест горизонтальный или это прокрутка
const BACK_RATIO = 0.35 // доля ширины экрана, после которой уходим назад
const BACK_VELOCITY = 0.6 // px/мс: быстрый взмах тоже считается…
const MIN_FLICK = 60 // …но только если протянули хотя бы столько
const EASE = 'cubic-bezier(0.2, 0.8, 0.2, 1)' // мягкое замедление, как у iOS
const OUT_MS = 260
const IN_MS = 300
const PARALLAX = 0.25 // предыдущий экран выезжает с четверти ширины

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

/** Сбрасывает стили жеста, когда анимация закончилась. */
function clearAfter(root: HTMLElement, ms: number) {
  window.setTimeout(() => {
    root.style.transition = ''
    root.style.transform = ''
    root.style.opacity = ''
    document.documentElement.classList.remove('swipe-back')
  }, ms)
}

export function useSwipeBack(onBack: (() => void) | null) {
  useEffect(() => {
    const root = document.getElementById('root')
    if (!root || !onBack) return

    let startX = 0
    let startY = 0
    let lastX = 0
    let lastTime = 0
    let velocity = 0
    let dx = 0
    // idle — ждём касания, pending — ещё не ясно направление, swiping — тянем экран, ignored — не наш жест
    let state: 'idle' | 'pending' | 'swiping' | 'ignored' = 'idle'

    const move = (x: number, ms: number) => {
      root.style.transition = ms ? `transform ${ms}ms ${EASE}` : 'none'
      root.style.transform = `translate3d(${x}px, 0, 0)`
    }

    const onStart = (e: TouchEvent) => {
      if (e.touches.length !== 1 || blocksSwipe(e.target)) {
        state = 'ignored'
        return
      }
      const t = e.touches[0]
      startX = lastX = t.clientX
      startY = t.clientY
      lastTime = e.timeStamp
      velocity = 0
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
        startX = t.clientX // экран начинает ехать с места, где жест распознан, без рывка
        document.documentElement.classList.add('swipe-back')
      }
      e.preventDefault() // не даём странице прокручиваться, пока тянем
      // Скорость сглаживаем, чтобы один дёрганый кадр не решал исход жеста
      const dt = Math.max(1, e.timeStamp - lastTime)
      velocity = velocity * 0.6 + ((t.clientX - lastX) / dt) * 0.4
      lastX = t.clientX
      lastTime = e.timeStamp
      dx = Math.max(0, t.clientX - startX)
      move(dx, 0)
    }

    const onEnd = () => {
      if (state !== 'swiping') {
        state = 'idle'
        return
      }
      state = 'idle'
      const width = window.innerWidth
      const goBack = dx > width * BACK_RATIO || (dx > MIN_FLICK && velocity > BACK_VELOCITY)
      if (!goBack) {
        // Не дотянули — экран мягко возвращается на место
        move(0, OUT_MS)
        clearAfter(root, OUT_MS)
        return
      }
      // Чем быстрее смахнули, тем быстрее уезжает экран
      const outMs = Math.round(
        Math.min(OUT_MS, Math.max(140, ((width - dx) / Math.max(velocity, 1)) * 1.2)),
      )
      move(width, outMs)
      window.setTimeout(() => {
        haptic.select()
        onBack()
        // Предыдущий экран выезжает слева с небольшим сдвигом и проявляется
        root.style.transition = 'none'
        root.style.transform = `translate3d(${-width * PARALLAX}px, 0, 0)`
        root.style.opacity = '0.6'
        requestAnimationFrame(() =>
          requestAnimationFrame(() => {
            root.style.transition = `transform ${IN_MS}ms ${EASE}, opacity ${IN_MS}ms ${EASE}`
            root.style.transform = 'translate3d(0, 0, 0)'
            root.style.opacity = '1'
            clearAfter(root, IN_MS)
          }),
        )
      }, outMs)
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
      // Анимацию перехода не трогаем: она сама уберёт стили по окончании
      if (state === 'swiping') clearAfter(root, 0)
    }
  }, [onBack])
}
