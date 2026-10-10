import type { Analysis, Health, Job, ScoreSummary, SearchProfile, Stats } from '../lib/types'

export function makeScore(overrides: Partial<ScoreSummary> = {}): ScoreSummary {
  return {
    overall_score: 91,
    band: 'Excellent',
    recommendation: 'APPLY',
    priority: 'HIGH',
    technical: 94,
    experience: 100,
    seniority: 85,
    location: 100,
    authorization: 80,
    role: 100,
    domain: 70,
    matched: ['iOS', 'Swift', 'UIKit'],
    gaps: ['CI/CD experience'],
    model: 'groq:openai/gpt-oss-120b',
    prompt_version: 'job_analysis_v1',
    analyzed_at: '2026-10-08T10:00:00',
    ...overrides,
  }
}

export function makeJob(overrides: Partial<Job> = {}): Job {
  return {
    id: 1,
    title: 'Senior iOS Engineer',
    company: 'Northwind',
    location: 'Remote, Worldwide',
    remote: true,
    workplace: 'remote',
    url: 'https://example.com/jobs/1',
    source: 'greenhouse',
    posted_date: null,
    salary_min: 150000,
    salary_max: 190000,
    salary_currency: 'USD',
    employment_type: 'full-time',
    required_skills: ['iOS', 'Swift', 'UIKit'],
    preferred_skills: ['SwiftUI'],
    minimum_years: 3,
    sponsorship: 'unknown',
    relevant: true,
    role_tier: 'primary',
    filter_reasons: [],
    user_decision: null,
    parsing_error: null,
    analysis_status: null,
    score: makeScore(),
    created_at: '2026-10-07T10:00:00',
    ...overrides,
  }
}

export function makeAnalysis(overrides: Partial<Analysis> = {}): Analysis {
  return {
    overall_score: 91,
    band: 'Excellent',
    recommendation: 'APPLY',
    priority: 'HIGH',
    summary: 'Strong overlap in Swift and UIKit.',
    confirmed_matches: [{ requirement: 'iOS experience', evidence_ref: 'NineSol', evidence: 'Shipped iOS features.' }],
    partial_matches: [{ requirement: 'Payments', evidence_ref: 'Forage SDK', note: 'No subscription billing shown.' }],
    gaps: ['CI/CD experience'],
    uncertain_requirements: ['Ownership mindset'],
    risks: ['Your legal work authorization is not confirmed.'],
    skill_coverage: { covered: ['iOS', 'Swift'], missing: ['GraphQL'] },
    scored_by: { ai: ['technical'], rules: ['experience'] },
    provider: 'groq',
    model: 'openai/gpt-oss-120b',
    prompt_version: 'job_analysis_v1',
    profile_version: 'v2',
    ...overrides,
  }
}

export const unscoredJob = (overrides: Partial<Job> = {}) => makeJob({ id: 2, title: 'iOS Engineer', company: 'Marrow', score: null, ...overrides })

export const stats: Stats = { found: 312, relevant: 41, filtered_out: 271, saved: 1, rejected: 3, analyzed: 7, high_fit: 3 }
export const emptyStats: Stats = { found: 0, relevant: 0, filtered_out: 0, saved: 0, rejected: 0, analyzed: 0, high_fit: 0 }

export const searchProfile: SearchProfile = {
  target_roles: ['iOS Engineer'],
  locations: ['Remote'],
  employment_types: ['Full-time'],
  minimum_score: 80,
  exclude_keywords: ['Principal'],
  companies: { greenhouse: ['stripe'], lever: [], ashby: ['ramp'] },
  company_names: { openai: 'OpenAI' },
}

export const health: Health = { backend: true, database: true, groq: true, ollama: false, playwright: false }
export const ai = { providers: [{ name: 'groq', configured: true, cooldown_seconds: 0 }] }
