import { QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { AppRoutes } from '../App'
import { ToastProvider } from '../components/ui/Toaster'
import { makeQueryClient } from '../lib/queryClient'
import { ai, health, searchProfile, stats } from './fixtures'

type Handler = (url: URL, init?: RequestInit) => unknown
export type Routes = Record<string, Handler | unknown>

export const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

/** Replaces fetch. Keys look like "GET /api/jobs". Unknown requests answer 404 so gaps are loud. */
export function mockApi(routes: Routes) {
  const calls: { method: string; path: string; search: URLSearchParams; body: unknown }[] = []
  const all: Routes = {
    'GET /api/jobs/stats': stats,
    'GET /api/health': health,
    'GET /api/ai/status': ai,
    'GET /api/search-profile': searchProfile,
    ...routes,
  }
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost')
    const method = (init?.method ?? 'GET').toUpperCase()
    calls.push({ method, path: url.pathname, search: url.searchParams, body: init?.body ? JSON.parse(String(init.body)) : undefined })
    const route = all[`${method} ${url.pathname}`]
    if (route === undefined) return json({ detail: `no mock for ${method} ${url.pathname}` }, 404)
    const value = typeof route === 'function' ? await (route as Handler)(url, init) : route
    return value instanceof Response ? value : json(value)
  })
  vi.stubGlobal('fetch', fetchMock)
  return {
    calls,
    called: (method: string, path: string) => calls.filter((c) => c.method === method && c.path === path),
  }
}

export function renderApp(route = '/') {
  return render(
    <QueryClientProvider client={makeQueryClient({ retry: false })}>
      <ToastProvider>
        <MemoryRouter initialEntries={[route]}>
          <AppRoutes />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}
