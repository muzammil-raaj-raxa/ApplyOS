import { AnimatePresence } from 'motion/react'
import { useMemo, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Dossier } from '../components/jobs/Dossier'
import { JobFilters } from '../components/jobs/JobFilters'
import { JobRow } from '../components/jobs/JobRow'
import { Button } from '../components/ui/Button'
import { JobListSkeleton } from '../components/ui/Skeleton'
import { EmptyState, ErrorState } from '../components/ui/StateBlock'
import { useActions } from '../hooks/actions'
import { useDecide } from '../hooks/decisions'
import { useJobs, useScoreJob, useStats } from '../hooks/queries'
import { useDebounced } from '../hooks/useDebounced'
import { useHotkeys } from '../hooks/useHotkeys'
import { applyFilters, hasActiveFilters, parseFilters } from '../lib/filters'
import { plural } from '../lib/format'
import type { JobFilters as Filters } from '../lib/types'

export function JobsPage() {
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const searchRef = useRef<HTMLInputElement>(null)

  const filters = useMemo(() => parseFilters(params), [params])
  const debouncedQuery = useDebounced(filters.q)
  const apiFilters = useMemo(() => ({ ...filters, q: debouncedQuery }), [filters, debouncedQuery])

  const jobsQuery = useJobs(apiFilters)
  const stats = useStats()
  const decide = useDecide()
  const scoreOne = useScoreJob()
  const { find, score, finding, scoring } = useActions()

  const items = useMemo(() => jobsQuery.data?.pages.flatMap((page) => page.items) ?? [], [jobsQuery.data])
  const total = jobsQuery.data?.pages[0]?.total ?? 0
  const jobId = params.get('job') ? Number(params.get('job')) : null
  const selectedIndex = jobId === null ? -1 : items.findIndex((job) => job.id === jobId)
  const selected = selectedIndex >= 0 ? items[selectedIndex] : undefined
  const scoringId = scoreOne.isPending ? (scoreOne.variables?.id ?? null) : null

  const setFilters = (patch: Partial<Filters>) => setParams(applyFilters(params, patch), { replace: true })

  const openJob = (id: number, replace = false) => {
    const next = new URLSearchParams(params)
    next.set('job', String(id))
    setParams(next, { replace })
  }
  const closeJob = () => {
    const next = new URLSearchParams(params)
    next.delete('job')
    setParams(next)
  }
  const step = (direction: -1 | 1) => {
    if (selectedIndex < 0) {
      if (items[0]) openJob(items[0].id, jobId !== null)
      return
    }
    const target = items[selectedIndex + direction]
    if (target) openJob(target.id, true)
  }

  useHotkeys({
    j: () => step(1),
    k: () => step(-1),
    s: () => selected && decide(selected.id, selected.user_decision === 'SAVED' ? 'clear' : 'save', selected.user_decision),
    x: () => selected && selected.user_decision !== 'REJECTED' && decide(selected.id, 'reject', selected.user_decision),
    a: () => selected && !selected.score && scoreOne.mutate({ id: selected.id }),
    '/': (event) => {
      event.preventDefault()
      searchRef.current?.focus()
    },
    Escape: () => jobId !== null && closeJob(),
  })

  const nothingFoundYet = stats.data?.found === 0
  const filtered = hasActiveFilters(filters)

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="text-display">Jobs</h1>
          <p className="mt-5 text-lead text-mist" aria-live="polite">
            {jobsQuery.isPending ? 'Loading…' : `${total} ${plural(total, 'job')} ${filtered ? 'match your filters' : 'to look at'}.`}
          </p>
        </div>
        <Button variant="secondary" loading={scoring} onClick={() => void score(5)}>
          {scoring ? 'Scoring…' : 'Score 5 jobs'}
        </Button>
      </div>

      <div className="mt-10" inert={jobId !== null}>
        <JobFilters filters={filters} query={filters.q} onQuery={(q) => setFilters({ q })} onChange={setFilters} searchRef={searchRef} />

        <div className="mt-6">
          {jobsQuery.isPending ? (
            <JobListSkeleton />
          ) : jobsQuery.error && items.length === 0 ? (
            <ErrorState error={jobsQuery.error} onRetry={() => void jobsQuery.refetch()} />
          ) : items.length === 0 ? (
            nothingFoundYet ? (
              <EmptyState
                title="No jobs yet."
                action={
                  <>
                    <Button variant="primary" loading={finding} onClick={() => void find()}>
                      Find new jobs
                    </Button>
                    <Button onClick={() => navigate('/sources')}>Check your sources</Button>
                  </>
                }
              >
                ApplyOS has not looked anywhere yet. It will check the companies listed in Sources and keep what fits your roles.
              </EmptyState>
            ) : (
              <EmptyState
                title={filtered ? 'Nothing matches these filters.' : 'Nothing to show here.'}
                action={
                  filtered ? (
                    <Button onClick={() => setParams(new URLSearchParams(jobId !== null ? { job: String(jobId) } : {}), { replace: true })}>Clear filters</Button>
                  ) : undefined
                }
              >
                {filtered ? 'Loosen a filter, or include jobs that were filtered out before scoring.' : 'Everything has been rejected or filtered out.'}
              </EmptyState>
            )
          ) : (
            <>
              <ul>
                <AnimatePresence initial={false}>
                  {items.map((job) => (
                    <JobRow
                      key={job.id}
                      job={job}
                      selected={job.id === jobId}
                      ruleId="job-rule"
                      scoring={scoringId === job.id}
                      onOpen={(id) => openJob(id)}
                      onDecision={decide}
                      onScore={(id) => scoreOne.mutate({ id })}
                    />
                  ))}
                </AnimatePresence>
              </ul>
              <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
                {jobsQuery.hasNextPage && (
                  <Button loading={jobsQuery.isFetchingNextPage} onClick={() => void jobsQuery.fetchNextPage()}>
                    Show more
                  </Button>
                )}
                <p className="text-label font-normal text-fog">
                  Showing {items.length} of {total}
                </p>
                <p className="hidden text-label font-normal text-fog md:block">J and K to move, S to save, X to reject, A to score, / to search</p>
              </div>
            </>
          )}
        </div>
      </div>

      <AnimatePresence>
        {jobId !== null && (
          <Dossier
            key="dossier"
            jobId={jobId}
            onClose={closeJob}
            onStep={step}
            canStep={{ prev: selectedIndex > 0, next: selectedIndex >= 0 && selectedIndex < items.length - 1 }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

