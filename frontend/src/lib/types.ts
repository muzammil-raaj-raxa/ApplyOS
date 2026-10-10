// Shapes returned by the ApplyOS backend (backend/app/api/*).

export type Workplace = 'remote' | 'hybrid' | 'onsite' | 'unknown'
export type Decision = 'SAVED' | 'REJECTED' | null

export interface ScoreSummary {
  overall_score: number
  band: string | null
  recommendation: 'APPLY' | 'REVIEW' | 'SKIP' | null
  priority: string | null
  technical: number
  experience: number
  seniority: number
  location: number
  authorization: number
  role: number
  domain: number
  matched: string[]
  gaps: string[]
  model: string
  prompt_version: string
  analyzed_at: string | null
}

export interface Job {
  id: number
  title: string
  company: string
  location: string | null
  remote: boolean | null
  workplace: Workplace | null
  url: string
  source: string
  posted_date: string | null
  salary_min: number | null
  salary_max: number | null
  salary_currency: string | null
  employment_type: string | null
  required_skills: string[]
  preferred_skills: string[]
  minimum_years: number | null
  sponsorship: string | null
  relevant: boolean | null
  role_tier: 'primary' | 'secondary' | 'unrelated' | null
  filter_reasons: string[]
  user_decision: Decision
  parsing_error: string | null
  analysis_status: string | null
  score: ScoreSummary | null
  created_at: string | null
  // detail only
  description?: string
  analysis?: Analysis | null
  analysis_error?: string | null
}

export interface MatchItem {
  requirement: string
  evidence_ref: string
  evidence: string
}

export interface PartialItem {
  requirement: string
  evidence_ref: string
  note: string
}

export interface Analysis {
  overall_score: number
  band: string
  recommendation: 'APPLY' | 'REVIEW' | 'SKIP'
  priority: string
  summary: string
  confirmed_matches: MatchItem[]
  partial_matches: PartialItem[]
  gaps: string[]
  uncertain_requirements: string[]
  risks: string[]
  skill_coverage: { covered: string[]; missing: string[] }
  scored_by: { ai: string[]; rules: string[] }
  provider: string
  model: string
  prompt_version: string
  profile_version: string
}

export interface JobsPage {
  total: number
  items: Job[]
}

export interface Stats {
  found: number
  relevant: number
  filtered_out: number
  saved: number
  rejected: number
  analyzed: number
  high_fit: number
}

export interface SearchProfile {
  target_roles: string[]
  locations: string[]
  employment_types: string[]
  minimum_score: number
  exclude_keywords: string[]
  companies: Record<string, string[]>
  company_names: Record<string, string>
}

export interface Health {
  backend: boolean
  database: boolean
  groq: boolean
  ollama: boolean
  playwright: boolean
}

export interface AiStatus {
  providers: { name: string; configured: boolean; cooldown_seconds: number }[]
}

export interface DiscoverySummary {
  fetched: number
  new: number
  relevant: number
  filtered_out: number
  already_known: number
  cross_source_duplicates: number
  parse_failures: number
  errors: string[]
}

export interface BatchSummary {
  analyzed: number
  needs_review: number
  pending: number
  stopped_reason: string | null
  results: { id: number; title: string; company: string; overall_score?: number; recommendation?: string; status?: string }[]
}

export interface AnalyzeResult {
  created: boolean
  analysis: Analysis
}

export interface JobFilters {
  q: string
  status: 'active' | 'saved' | 'rejected' | 'all'
  fit: 'any' | 'unscored' | '70' | '80' | '90'
  where: 'any' | 'remote' | 'hybrid' | 'onsite'
  sort: 'best' | 'new'
  all: boolean
}
