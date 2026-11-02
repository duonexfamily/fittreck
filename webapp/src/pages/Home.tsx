import { useQuery } from '@tanstack/react-query'
import { Link, Navigate } from 'react-router'

import { getMe, getTargets } from '../api/client'
import TargetsCard from '../components/TargetsCard'
import { isInTelegram } from '../lib/telegram'

const SECTIONS = [
  { emoji: '🍽', title: 'Питание', hint: 'Скоро' },
  { emoji: '🏋️', title: 'Тренировки', hint: 'Скоро' },
  { emoji: '😴', title: 'Сон и самочувствие', hint: 'Скоро' },
  { emoji: '📈', title: 'Прогресс', hint: 'Скоро' },
]

export default function Home() {
  const me = useQuery({ queryKey: ['me'], queryFn: getMe, enabled: isInTelegram })
  const onboarded = Boolean(me.data?.onboarded_at)
  const targets = useQuery({ queryKey: ['targets'], queryFn: getTargets, enabled: onboarded })

  if (!isInTelegram) {
    return (
      <main className="p-4">
        <h1 className="text-xl font-semibold">FitTrack</h1>
        <p className="mt-2 text-hint">Откройте приложение через бота в Telegram.</p>
      </main>
    )
  }

  if (me.data && !onboarded) return <Navigate to="/onboarding" replace />

  return (
    <main className="p-4">
      <h1 className="text-xl font-semibold">
        {me.data ? `Привет, ${me.data.first_name}!` : 'FitTrack'}
      </h1>
      {me.isError && <p className="mt-2 text-hint">Не удалось загрузить профиль.</p>}

      {targets.data && (
        <div className="mt-4">
          <TargetsCard targets={targets.data} />
          <Link to="/onboarding" className="mt-2 inline-block text-sm text-link">
            Изменить анкету
          </Link>
        </div>
      )}

      <ul className="mt-4 grid grid-cols-2 gap-3">
        {SECTIONS.map((s) => (
          <li key={s.title} className="rounded-2xl bg-bg-secondary p-4">
            <div className="text-2xl">{s.emoji}</div>
            <div className="mt-2 font-medium">{s.title}</div>
            <div className="text-sm text-hint">{s.hint}</div>
          </li>
        ))}
      </ul>

      <p className="mt-6 text-xs text-hint">
        Приложение носит информационный характер и не заменяет консультацию врача, диетолога или
        тренера.
      </p>
    </main>
  )
}
