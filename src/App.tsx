import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './contexts/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Navbar } from './components/Navbar'
import Auth from './pages/Auth'
import Dashboard from './pages/Dashboard'
import Profile from './pages/Profile'
import Artifacts from './pages/Artifacts'
import ArtifactDetail from './pages/ArtifactDetail'
import ArtifactNew from './pages/ArtifactNew'
import Bugs from './pages/Bugs'
import BugDetail from './pages/BugDetail'
import BugNew from './pages/BugNew'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <div className="min-h-screen bg-gray-50">
            <Navbar />
            <main className="pt-16">
              <Routes>
                <Route path="/auth" element={<Auth />} />
                <Route
                  path="/dashboard"
                  element={
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/profile"
                  element={
                    <ProtectedRoute>
                      <Profile />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/artifacts"
                  element={
                    <ProtectedRoute>
                      <Artifacts />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/artifacts/new"
                  element={
                    <ProtectedRoute>
                      <ArtifactNew />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/artifacts/:id"
                  element={
                    <ProtectedRoute>
                      <ArtifactDetail />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/bugs"
                  element={
                    <ProtectedRoute>
                      <Bugs />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/bugs/new"
                  element={
                    <ProtectedRoute>
                      <BugNew />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/bugs/:id"
                  element={
                    <ProtectedRoute>
                      <BugDetail />
                    </ProtectedRoute>
                  }
                />
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </main>
            <Toaster position="top-right" />
          </div>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
