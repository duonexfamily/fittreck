import { Component, type ReactNode } from 'react'

interface State {
  error: Error | null
}

// После деплоя у старой страницы ссылки на чанки, которых уже нет
const isStaleChunk = (error: Error) =>
  /dynamically imported module|Importing a module script failed|ChunkLoadError/i.test(
    error.message,
  )

/** Ошибка отрисовки — понятный экран с кнопкой вместо белого листа. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children
    const stale = isStaleChunk(error)
    return (
      <main className="p-4">
        <h1 className="text-xl font-semibold">
          {stale ? 'Вышла новая версия' : 'Что-то пошло не так'}
        </h1>
        <p className="mt-2 text-hint">
          {stale
            ? 'Обновите приложение, чтобы продолжить. Данные сохранены.'
            : 'Попробуйте обновить экран. Если ошибка повторится — закройте приложение и откройте снова из бота.'}
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-4 w-full rounded-xl bg-button px-4 py-3 text-button-text"
        >
          Обновить
        </button>
      </main>
    )
  }
}
