import type {
  AiStatus,
  AnalyzeResult,
  BatchSummary,
  DiscoverySummary,
  Health,
  Job,
  JobFilters,
  JobsPage,
  SearchProfile,
  Stats,
} from './types'

export const PAGE_SIZE = 30

export class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

/** FastAPI sends detail as a string, or as a list of validation problems. */
export function describeDetail(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (item && typeof item === 'object' && 'msg' in item) {
          const where = Array.isArray((item as { loc?: unknown[] }).loc)
            ? ((item as { loc: unknown[] }).loc.filter((p) => p !== 'body').join(' / '))
            : ''
          return where ? `${where}: ${String((item as { msg: unknown }).msg)}` : String((item as { msg: unknown }).msg)
        }
        return ''
      })
      .filter(Boolean)
    if (parts.length) return parts.join('. ')
  }
  return fallback
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError(0, "Can't reach the backend. Start ApplyOS with ./scripts/start.sh and try again.")
  }
  if (!response.ok) {
    let detail: unknown = null
    try {
      detail = (await response.json())?.detail
    } catch {
      // not JSON: fall through to the generic message
    }
    throw new ApiError(response.status, describeDetail(detail, `The backend answered ${response.status}.`))
  }
  return (await response.json()) as T
}

export function jobsQuery(filters: JobFilters, offset: number): string {
  const params = new URLSearchParams()
  if (filters.q.trim()) params.set('q', filters.q.trim())
  if (filters.status === 'saved') params.set('decision', 'saved')
  if (filters.status === 'rejected') params.set('decision', 'rejected')
  if (filters.status === 'all') params.set('decision', 'all')
  if (filters.fit === 'unscored') params.set('scored', 'false')
  else if (filters.fit !== 'any') params.set('min_score', filters.fit)
  if (filters.where !== 'any') params.set('workplace', filters.where)
  params.set('sort', filters.sort === 'best' ? 'score' : 'newest')
  if (filters.all) params.set('include_filtered', 'true')
  params.set('limit', String(PAGE_SIZE))
  params.set('offset', String(offset))
  return params.toString()
}

const post = <T>(path: string) => request<T>(path, { method: 'POST' })

export const api = {
  jobs: (filters: JobFilters, offset: number) => request<JobsPage>(`/api/jobs?${jobsQuery(filters, offset)}`),
  job: (id: number) => request<Job>(`/api/jobs/${id}`),
  stats: () => request<Stats>('/api/jobs/stats'),
  findJobs: () => post<DiscoverySummary>('/api/jobs/search'),
  scoreJobs: (limit: number) => post<BatchSummary>(`/api/jobs/analyze?limit=${limit}`),
  scoreJob: (id: number, force: boolean) => post<AnalyzeResult>(`/api/jobs/${id}/analyze?force=${force}`),
  save: (id: number) => post<Job>(`/api/jobs/${id}/save`),
  reject: (id: number) => post<Job>(`/api/jobs/${id}/reject`),
  clearDecision: (id: number) => request<Job>(`/api/jobs/${id}/decision`, { method: 'DELETE' }),
  searchProfile: () => request<SearchProfile>('/api/search-profile'),
  saveSearchProfile: (profile: SearchProfile) =>
    request<SearchProfile>('/api/search-profile', { method: 'PUT', body: JSON.stringify(profile) }),
  health: () => request<Health>('/api/health'),
  aiStatus: () => request<AiStatus>('/api/ai/status'),
}
