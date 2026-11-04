import type { DayStats } from '../api/client'

// Длиннее — показываем по неделям: дневные столбики уже не различить
export const WEEKLY_AFTER_DAYS = 120

const avg = (values: (number | null)[]): number | null => {
  const present = values.filter((v): v is number => v !== null)
  return present.length ? present.reduce((a, b) => a + b, 0) / present.length : null
}

/** Сворачивает дни в недели: оценки, вес, калории и сон — среднее, тренировки — сумма. */
export function byWeek(days: DayStats[]): DayStats[] {
  const weeks: DayStats[] = []
  for (let i = 0; i < days.length; i += 7) {
    const chunk = days.slice(i, i + 7)
    const pick = <K extends keyof DayStats>(key: K) => chunk.map((d) => d[key] as number | null)
    const sleep = avg(pick('sleep_minutes'))
    weeks.push({
      date: chunk[0].date,
      weight_kg: avg(pick('weight_kg')),
      kcal: avg(pick('kcal')),
      sleep_minutes: sleep === null ? null : Math.round(sleep),
      sleep_quality: avg(pick('sleep_quality')),
      energy: avg(pick('energy')),
      stress: avg(pick('stress')),
      mood: avg(pick('mood')),
      workouts: chunk.reduce((s, d) => s + d.workouts, 0),
      volume_kg: chunk.reduce((s, d) => s + d.volume_kg, 0),
    })
  }
  return weeks
}
