import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Shell } from './components/shell/Shell'
import { ToastProvider } from './components/ui/Toaster'
import { makeQueryClient } from './lib/queryClient'
import { JobsPage } from './pages/Jobs'
import { SourcesPage } from './pages/Sources'
import { TodayPage } from './pages/Today'

const queryClient = makeQueryClient()

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<TodayPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="sources" element={<SourcesPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  )
}
