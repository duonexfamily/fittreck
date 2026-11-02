import { Navigate, Route, Routes } from 'react-router'

import Home from './pages/Home'
import Onboarding from './pages/Onboarding'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
