import { Routes, Route, Navigate } from 'react-router-dom'
import ThemeProvider from './context/ThemeProvider'
import AuthProvider, { useAuth } from './context/AuthProvider'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import ChoosePlan from './pages/ChoosePlan'
import ComingSoon from './pages/ComingSoon'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route
            path="/choose-plan"
            element={
              <ProtectedRoute>
                <ChoosePlan />
              </ProtectedRoute>
            }
          />
          <Route
            path="/coming-soon"
            element={
              <ProtectedRoute>
                <ComingSoon />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </ThemeProvider>
  )
}
