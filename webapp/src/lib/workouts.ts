import type { ExerciseKind, MuscleGroup, SetValues } from '../api/client'

export const MUSCLE_LABELS: Record<MuscleGroup, string> = {
  chest: 'Грудь',
  back: 'Спина',
  shoulders: 'Плечи',
  arms: 'Руки',
  legs: 'Ноги',
  core: 'Пресс и кор',
  full_body: 'Всё тело',
}

export const KIND_LABELS: Record<ExerciseKind, { label: string; hint: string }> = {
  strength: { label: 'Силовое', hint: 'повторения × вес' },
  cardio: { label: 'Кардио', hint: 'время, дистанция' },
  stretch: { label: 'На время', hint: 'планка, растяжка' },
}

export const MUSCLE_GROUPS = Object.keys(MUSCLE_LABELS) as MuscleGroup[]
export const EXERCISE_KINDS = Object.keys(KIND_LABELS) as ExerciseKind[]

/** Поля формы подхода — строки, как ввёл пользователь. */
export interface SetRaw {
  reps: string
  weight: string
  // Кардио — минуты, «на время» — секунды
  time: string
  km: string
}

export const EMPTY_SET_RAW: SetRaw = { reps: '', weight: '', time: '', km: '' }

/** Единица времени в форме: кардио длится минуты, планка — секунды. */
export const timeUnit = (kind: ExerciseKind) => (kind === 'cardio' ? 'мин' : 'сек')

/** Поля формы по сохранённому подходу — чтобы следующий подход начинался с прошлых значений. */
export function setToRaw(kind: ExerciseKind, s: SetValues): SetRaw {
  // Минуты кардио — с точностью до десятых
  const minutes = (sec: number) => Math.round(sec / 6) / 10
  const time =
    s.duration_s === null ? '' : String(kind === 'cardio' ? minutes(s.duration_s) : s.duration_s)
  return {
    reps: s.reps === null ? '' : String(s.reps),
    weight: s.weight_kg === null ? '' : String(s.weight_kg),
    time,
    km: s.distance_m === null ? '' : String(s.distance_m / 1000),
  }
}

const parseOptional = (raw: string) => (raw.trim() === '' ? null : Number(raw.replace(',', '.')))

/**
 * Подход из полей формы. null — значения не подходят.
 * Правила и границы совпадают с backend (app/services/workouts.py, app/api/schemas/workouts.py).
 */
export function parseSet(kind: ExerciseKind, raw: SetRaw): SetValues | null {
  const empty: SetValues = { reps: null, weight_kg: null, duration_s: null, distance_m: null }
  const inRange = (v: number | null, min: number, max: number) =>
    v === null || (Number.isFinite(v) && v >= min && v <= max)

  if (kind === 'strength') {
    const reps = parseOptional(raw.reps)
    const w = parseOptional(raw.weight)
    const weight = w === null ? null : Math.round(w * 100) / 100
    if (reps === null || !Number.isInteger(reps) || !inRange(reps, 1, 1000)) return null
    if (!inRange(weight, 0, 500)) return null
    return { ...empty, reps, weight_kg: weight }
  }

  const t = parseOptional(raw.time)
  const duration = t === null ? null : Math.round(kind === 'cardio' ? t * 60 : t)
  if (!inRange(duration, 1, 86400)) return null
  if (kind === 'stretch') return duration === null ? null : { ...empty, duration_s: duration }

  const km = parseOptional(raw.km)
  const distance = km === null ? null : Math.round(km * 1000)
  if (!inRange(distance, 1, 1_000_000)) return null
  if (duration === null && distance === null) return null
  return { ...empty, duration_s: duration, distance_m: distance }
}

/** Число с запятой, без лишних нулей: 62.5 → «62,5». */
export function fmtNumber(v: number, digits = 2): string {
  const k = 10 ** digits
  return String(Math.round(v * k) / k).replace('.', ',')
}

/** 45 → «45 с», 90 → «1:30», 3725 → «1:02:05». */
export function fmtDuration(s: number): string {
  if (s < 60) return `${s} с`
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = String(s % 60).padStart(2, '0')
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${sec}` : `${m}:${sec}`
}

export const fmtDistance = (m: number) => (m >= 1000 ? `${fmtNumber(m / 1000)} км` : `${m} м`)

/** Подход одной строкой: «10 × 60 кг», «20:00 · 3 км», «1:00». */
export function fmtSet(s: SetValues): string {
  const parts: string[] = []
  if (s.reps !== null) {
    parts.push(s.weight_kg ? `${s.reps} × ${fmtNumber(s.weight_kg)} кг` : `${s.reps} повт.`)
  }
  if (s.duration_s !== null) parts.push(fmtDuration(s.duration_s))
  if (s.distance_m !== null) parts.push(fmtDistance(s.distance_m))
  return parts.join(' · ')
}

/** Подпись к нагрузке RPE. */
export function rpeHint(rpe: number): string {
  if (rpe <= 3) return 'легко'
  if (rpe <= 6) return 'умеренно'
  if (rpe <= 8) return 'тяжело'
  return 'на пределе'
}
