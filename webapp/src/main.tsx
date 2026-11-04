import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'

import { ApiError } from './api/client'
import App from './App'
import './index.css'
import { markSessionExpired } from './lib/session'
import { initTelegram } from './lib/telegram'

initTelegram()

const onError = (error: Error) => {
  if (error instanceof ApiError && error.status === 401) markSessionExpired()
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError }),
  mutationCache: new MutationCache({ onError }),
  defaultOptions: {
    queries: {
      // Ответ 4xx повтором не исправить — сразу показываем ошибку
      retry: (count, error) =>
        count < 1 && !(error instanceof ApiError && error.status >= 400 && error.status < 500),
      staleTime: 30_000,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
