import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router'

import Home from './pages/Home'
import Onboarding from './pages/Onboarding'

// Экраны разделов грузятся по требованию — главный экран открывается быстрее
const Nutrition = lazy(() => import('./pages/Nutrition'))
const NutritionAdd = lazy(() => import('./pages/NutritionAdd'))
const MealItemEdit = lazy(() => import('./pages/MealItemEdit'))
const Weight = lazy(() => import('./pages/Weight'))

export default function App() {
  return (
    <Suspense fallback={<p className="p-4 text-hint">Загрузка…</p>}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/nutrition" element={<Nutrition />} />
        <Route path="/nutrition/add" element={<NutritionAdd />} />
        <Route path="/nutrition/item/:id" element={<MealItemEdit />} />
        <Route path="/weight" element={<Weight />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
