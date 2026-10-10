import type { JobFilters } from './types'

export const DEFAULT_FILTERS: JobFilters = { q: '', status: 'active', fit: 'any', where: 'any', sort: 'best', all: false }

const ALLOWED = {
  status: ['active', 'saved', 'rejected', 'all'],
  fit: ['any', 'unscored', '70', '80', '90'],
  where: ['any', 'remote', 'hybrid', 'onsite'],
  sort: ['best', 'new'],
} as const

function pick<K extends keyof typeof ALLOWED>(params: URLSearchParams, key: K): JobFilters[K] {
  const value = params.get(key)
  return ((ALLOWED[key] as readonly string[]).includes(value ?? '') ? value : DEFAULT_FILTERS[key]) as JobFilters[K]
}

/** The address bar is the source of truth, so filters survive reloads and the back button. */
export function parseFilters(params: URLSearchParams): JobFilters {
  return {
    q: params.get('q') ?? '',
    status: pick(params, 'status'),
    fit: pick(params, 'fit'),
    where: pick(params, 'where'),
    sort: pick(params, 'sort'),
    all: params.get('all') === '1',
  }
}

export function applyFilters(params: URLSearchParams, patch: Partial<JobFilters>): URLSearchParams {
  const next = new URLSearchParams(params)
  const merged = { ...parseFilters(params), ...patch }
  for (const [key, value] of Object.entries(merged) as [keyof JobFilters, string | boolean][]) {
    const isDefault = value === DEFAULT_FILTERS[key]
    const param = key === 'all' ? (value ? '1' : '') : String(value)
    if (isDefault || !param) next.delete(key)
    else next.set(key, param)
  }
  return next
}

export function hasActiveFilters(filters: JobFilters): boolean {
  return (Object.keys(DEFAULT_FILTERS) as (keyof JobFilters)[]).some((key) => filters[key] !== DEFAULT_FILTERS[key])
}
