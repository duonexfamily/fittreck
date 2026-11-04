import type { CheckinValues } from '../api/client'

export type ScoreKey = 'sleep_quality' | 'energy' | 'stress' | 'mood'

/** Подписи оценок 1–5. У стресса шкала обратная: 5 — сильный. */
export const SCORES: { key: ScoreKey; label: string; words: string[] }[] = [
  {
    key: 'sleep_quality',
    label: 'Качество сна',
    words: ['ужасно', 'плохо', 'так себе', 'хорошо', 'отлично'],
  },
  {
    key: 'energy',
    label: 'Энергия',
    words: ['нет сил', 'вяло', 'нормально', 'бодро', 'полон сил'],
  },
  {
    key: 'stress',
    label: 'Стресс',
    words: ['спокойно', 'небольшой', 'средний', 'высокий', 'очень высокий'],
  },
  {
    key: 'mood',
    label: 'Настроение',
    words: ['плохое', 'грустно', 'ровное', 'хорошее', 'отличное'],
  },
]

/** Длительность сна по времени на часах: отход позже подъёма — значит, накануне вечером. */
export function sleepMinutes(bed: string, wake: string): number {
  const toMin = (t: string) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5))
  return (((toMin(wake) - toMin(bed)) % 1440) + 1440) % 1440
}

/** 450 → «7 ч 30 мин». */
export function fmtSleep(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `${m} мин`
  return m === 0 ? `${h} ч` : `${h} ч ${m} мин`
}

/** «23:30:00» → «23:30» — для поля type="time". */
export const toHHMM = (t: string | null) => (t ? t.slice(0, 5) : null)

export const EMPTY_CHECKIN: CheckinValues = {
  bed_time: null,
  wake_time: null,
  sleep_quality: null,
  energy: null,
  stress: null,
  mood: null,
  note: null,
}
