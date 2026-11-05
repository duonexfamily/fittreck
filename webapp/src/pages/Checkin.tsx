import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'

import { type Checkin as CheckinData, getCheckins, getMe, putCheckin } from '../api/client'
import { useBackButton } from '../hooks/useBackButton'
import { useMainButton } from '../hooks/useMainButton'
import {
  EMPTY_CHECKIN,
  SCORES,
  type ScoreKey,
  fmtSleep,
  sleepMinutes,
  toHHMM,
} from '../lib/checkin'
import { formatDay, shiftDate, todayIn } from '../lib/nutrition'
import { haptic } from '../lib/telegram'

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/
// Сколько дней показывать в истории под формой
const HISTORY_DAYS = 7
const DEFAULT_BED = '23:00'
const DEFAULT_WAKE = '07:00'

/** Оценка 1–5 кнопками. Повторное касание выбранной оценки снимает её. */
function ScoreField({
  label,
  words,
  value,
  onChange,
}: {
  label: string
  words: string[]
  value: number | null
  onChange: (v: number | null) => void
}) {
  return (
    <div className="rounded-2xl bg-bg-secondary p-4">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-hint">{label}</span>
        <span className="text-sm">{value === null ? '—' : words[value - 1]}</span>
      </div>
      <div className="mt-3 grid grid-cols-5 gap-2" role="radiogroup" aria-label={label}>
        {[1, 2, 3, 4, 5].map((v) => (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={v === value}
            onClick={() => {
              haptic.select()
              onChange(v === value ? null : v)
            }}
            className={`rounded-xl py-2 font-medium ${v === value ? 'bg-button text-button-text' : 'bg-bg'}`}
          >
            {v}
          </button>
        ))}
      </div>
    </div>
  )
}

function CheckinForm({
  date,
  existing,
  onSaved,
}: {
  date: string
  existing: CheckinData | undefined
  onSaved: () => Promise<void>
}) {
  const initial = existing ?? EMPTY_CHECKIN
  const [withSleep, setWithSleep] = useState(existing ? existing.bed_time !== null : true)
  const [bed, setBed] = useState(toHHMM(initial.bed_time) ?? DEFAULT_BED)
  const [wake, setWake] = useState(toHHMM(initial.wake_time) ?? DEFAULT_WAKE)
  const [scores, setScores] = useState<Record<ScoreKey, number | null>>({
    sleep_quality: initial.sleep_quality,
    energy: initial.energy,
    stress: initial.stress,
    mood: initial.mood,
  })
  const [note, setNote] = useState(initial.note ?? '')
  const [saved, setSaved] = useState(false)

  const timesValid = !withSleep || (bed !== '' && wake !== '')
  const filled = withSleep || Object.values(scores).some((v) => v !== null) || note.trim() !== ''

  const save = useMutation({
    mutationFn: () =>
      putCheckin(date, {
        bed_time: withSleep ? bed : null,
        wake_time: withSleep ? wake : null,
        ...scores,
        note: note.trim() || null,
      }),
    onSuccess: async () => {
      haptic.success()
      setSaved(true)
      await onSaved()
    },
    onError: () => haptic.error(),
  })
  const submit = useCallback(() => {
    if (!save.isPending) save.mutate()
  }, [save])
  useMainButton({
    text: 'Сохранить',
    onClick: submit,
    enabled: timesValid && filled,
    loading: save.isPending,
  })
  // Любая правка снимает отметку «Сохранено»
  const touch = () => setSaved(false)

  return (
    <div className="mt-4 grid gap-3">
      <section className="rounded-2xl bg-bg-secondary p-4">
        <label className="flex items-center justify-between gap-3">
          <span className="font-medium">Сон</span>
          <input
            type="checkbox"
            checked={withSleep}
            onChange={(e) => {
              touch()
              setWithSleep(e.target.checked)
            }}
            className="size-5 accent-button"
          />
        </label>
        {withSleep && (
          <>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <label className="rounded-xl bg-bg p-3">
                <span className="block text-xs text-hint">Лёг</span>
                <input
                  type="time"
                  value={bed}
                  onChange={(e) => {
                    touch()
                    setBed(e.target.value)
                  }}
                  className="w-full bg-transparent text-lg outline-none"
                />
              </label>
              <label className="rounded-xl bg-bg p-3">
                <span className="block text-xs text-hint">Встал</span>
                <input
                  type="time"
                  value={wake}
                  onChange={(e) => {
                    touch()
                    setWake(e.target.value)
                  }}
                  className="w-full bg-transparent text-lg outline-none"
                />
              </label>
            </div>
            {timesValid && (
              <p className="mt-2 text-sm text-hint">Сон: {fmtSleep(sleepMinutes(bed, wake))}</p>
            )}
          </>
        )}
      </section>

      {SCORES.map((s) => (
        <ScoreField
          key={s.key}
          label={s.label}
          words={s.words}
          value={scores[s.key]}
          onChange={(v) => {
            touch()
            setScores({ ...scores, [s.key]: v })
          }}
        />
      ))}

      <textarea
        value={note}
        onChange={(e) => {
          touch()
          setNote(e.target.value)
        }}
        maxLength={1000}
        rows={3}
        placeholder="Заметка: что повлияло на сон и самочувствие"
        className="w-full resize-none rounded-2xl bg-bg-secondary p-4 outline-none"
      />
      {save.isError && <p className="text-sm text-destructive">Не получилось сохранить.</p>}
      {saved && <p className="text-sm text-hint">Сохранено ✓</p>}
    </div>
  )
}

export default function Checkin() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [params, setParams] = useSearchParams()
  const me = useQuery({ queryKey: ['me'], queryFn: getMe })
  const today = todayIn(me.data?.timezone)
  const dateParam = params.get('date')
  const date = dateParam && DATE_RE.test(dateParam) && dateParam <= today ? dateParam : today
  const from = shiftDate(date, -(HISTORY_DAYS - 1))

  const list = useQuery({
    queryKey: ['checkins', from, date],
    queryFn: () => getCheckins(from, date),
    enabled: me.isSuccess,
  })

  useBackButton(useCallback(() => navigate('/'), [navigate]))

  const go = (delta: number) => {
    haptic.select()
    setParams({ date: shiftDate(date, delta) }, { replace: true })
  }
  const existing = list.data?.find((c) => c.date === date)
  const history = [...(list.data ?? [])].reverse()

  return (
    <main className="p-4 pb-10">
      <h1 className="page-title">Сон и самочувствие</h1>
      <div className="mt-3 flex items-center justify-between rounded-2xl bg-bg-secondary p-2">
        <button
          type="button"
          onClick={() => go(-1)}
          className="px-3 py-1 text-lg text-link"
          aria-label="Предыдущий день"
        >
          ‹
        </button>
        <span className="font-medium">{formatDay(date, today)}</span>
        <button
          type="button"
          onClick={() => go(1)}
          disabled={date >= today}
          className="px-3 py-1 text-lg text-link disabled:opacity-30"
          aria-label="Следующий день"
        >
          ›
        </button>
      </div>

      {list.isError && <p className="mt-4 text-hint">Не удалось загрузить чек-ин.</p>}
      {list.isPending && <p className="mt-4 text-hint">Загрузка…</p>}
      {list.isSuccess && (
        <CheckinForm
          key={date}
          date={date}
          existing={existing}
          onSaved={() => queryClient.invalidateQueries({ queryKey: ['checkins'] })}
        />
      )}

      {history.length > 0 && (
        <>
          <h2 className="mt-6 font-medium">Последние дни</h2>
          <ul className="mt-2 divide-y divide-bg rounded-2xl bg-bg-secondary px-4">
            {history.map((c) => (
              <li key={c.date}>
                <button
                  type="button"
                  onClick={() => setParams({ date: c.date }, { replace: true })}
                  className="flex w-full items-baseline justify-between gap-3 py-3 text-left"
                >
                  <span className="text-sm">{formatDay(c.date, today)}</span>
                  <span className="text-sm text-hint">
                    {[
                      c.sleep_minutes !== null && `😴 ${fmtSleep(c.sleep_minutes)}`,
                      c.energy !== null && `⚡ ${c.energy}/5`,
                      c.mood !== null && `🙂 ${c.mood}/5`,
                    ]
                      .filter(Boolean)
                      .join(' · ')}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      <p className="mt-6 text-xs text-hint">
        Приложение носит информационный характер и не заменяет консультацию врача. Если плохой сон
        или стресс держатся долго, обратитесь к специалисту.
      </p>
    </main>
  )
}
