import type { ScoreSummary, Workplace } from './types'

export interface Band {
  key: 'excellent' | 'strong' | 'worth' | 'weak' | 'poor'
  label: string
  color: string // CSS value, usable in style props and SVG style
  glow: boolean
}

/** One place that decides what a score means. The thresholds match the backend bands. */
export function bandFor(score: number): Band {
  if (score >= 90) return { key: 'excellent', label: 'Excellent fit', color: 'var(--color-mint)', glow: true }
  if (score >= 80) return { key: 'strong', label: 'Strong fit', color: 'var(--color-jade)', glow: true }
  if (score >= 70) return { key: 'worth', label: 'Worth a look', color: 'var(--color-apricot)', glow: false }
  if (score >= 60) return { key: 'weak', label: 'Weak fit', color: 'var(--color-clay)', glow: false }
  return { key: 'poor', label: 'Poor fit', color: 'var(--color-coral)', glow: false }
}

export interface Dimension {
  key: keyof Pick<ScoreSummary, 'technical' | 'experience' | 'seniority' | 'location' | 'authorization' | 'role' | 'domain'>
  label: string
  weight: number
  by: 'AI' | 'Rule'
  hint: string
}

/** Same weights as backend/app/jobs/scoring.py. They add up to 100. */
export const DIMENSIONS: Dimension[] = [
  { key: 'technical', label: 'Technical skills', weight: 30, by: 'AI', hint: 'How fully the required technologies are covered' },
  { key: 'experience', label: 'Experience', weight: 20, by: 'Rule', hint: 'Years the job asks for compared with yours' },
  { key: 'seniority', label: 'Seniority', weight: 15, by: 'AI', hint: 'Level the job expects compared with yours' },
  { key: 'location', label: 'Location', weight: 10, by: 'Rule', hint: 'Remote, hybrid or onsite against your preferences' },
  { key: 'authorization', label: 'Work authorization', weight: 10, by: 'Rule', hint: 'What the posting says about sponsorship' },
  { key: 'role', label: 'Role fit', weight: 10, by: 'Rule', hint: 'How close the title is to your target roles' },
  { key: 'domain', label: 'Domain', weight: 5, by: 'AI', hint: 'How close the product area is to your work' },
]

export const RECOMMENDATION_TEXT: Record<string, string> = {
  APPLY: 'Worth preparing an application',
  REVIEW: 'Review before deciding',
  SKIP: 'Probably skip',
}

export const WORKPLACE_TEXT: Record<Workplace, string> = {
  remote: 'Remote',
  hybrid: 'Hybrid',
  onsite: 'Onsite',
  unknown: 'Workplace unclear',
}

const SYMBOLS: Record<string, string> = { USD: '$', GBP: '£', EUR: '€' }

function shortMoney(value: number): string {
  return value >= 1000 ? `${Math.round(value / 1000)}k` : String(value)
}

export function formatSalary(min: number | null, max: number | null, currency: string | null): string | null {
  if (min == null && max == null) return null
  const symbol = currency ? (SYMBOLS[currency] ?? `${currency} `) : ''
  if (min != null && max != null && min !== max) return `${symbol}${shortMoney(min)} to ${symbol}${shortMoney(max)}`
  return `${symbol}${shortMoney((min ?? max) as number)}`
}

export function relativeTime(iso: string | null | undefined, now: number = Date.now()): string {
  if (!iso) return ''
  const stamp = Date.parse(iso.endsWith('Z') || /[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`)
  if (Number.isNaN(stamp)) return ''
  const seconds = Math.max(0, Math.round((now - stamp) / 1000))
  if (seconds < 45) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} h ago`
  const days = Math.round(hours / 24)
  if (days < 30) return `${days} d ago`
  return new Date(stamp).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

export function plural(count: number, one: string, many = `${one}s`): string {
  return count === 1 ? one : many
}

export function sourceName(source: string): string {
  return source.charAt(0).toUpperCase() + source.slice(1)
}
