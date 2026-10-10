import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { JobRow } from '../components/jobs/JobRow'
import { statusLines } from '../lib/status'
import { Button } from '../components/ui/Button'
import { Bar } from '../components/ui/Skeleton'
import { EmptyState } from '../components/ui/StateBlock'
import { AnimatedNumber } from '../components/viz/AnimatedNumber'
import { StageRings, type Stage } from '../components/viz/StageRings'
import { LAST_RUN_KEY, useActions, type LastRun } from '../hooks/actions'
import { useDecide } from '../hooks/decisions'
import { useAiStatus, useHealth, useJobs, useSearchProfile, useStats } from '../hooks/queries'
import { useElapsed } from '../hooks/useElapsed'
import { useIsNarrow } from '../hooks/useMedia'
import { DEFAULT_FILTERS } from '../lib/filters'
import { plural, relativeTime } from '../lib/format'
import { readStored } from '../lib/storage'
import type { Stats } from '../lib/types'

function headline(stats: Stats, minScore: number) {
  if (stats.found === 0) return { before: 'Nothing found', number: null, after: 'yet.', sub: 'Find new jobs and ApplyOS will check every company in Sources.' }
  if (stats.analyzed === 0) {
    return {
      before: '',
      number: stats.relevant,
      after: `${plural(stats.relevant, 'job')} match your roles.`,
      sub: 'None are scored yet. Score the most promising ones to see how well they fit you.',
    }
  }
  if (stats.high_fit === 0) {
    return { before: 'No strong fits', number: null, after: 'yet.', sub: `${stats.analyzed} scored so far. A strong fit means ${minScore} or higher out of 100.` }
  }
  return {
    before: '',
    number: stats.high_fit,
    after: `${plural(stats.high_fit, 'job')} ${stats.high_fit === 1 ? 'fits' : 'fit'} you well.`,
    sub: `${stats.analyzed} scored out of ${stats.relevant} relevant. A strong fit means ${minScore} or higher out of 100.`,
  }
}

function ratio(part: number, whole: number) {
  return whole > 0 ? Math.min(1, part / whole) : 0
}

export function TodayPage() {
  const navigate = useNavigate()
  const narrow = useIsNarrow()
  const stats = useStats()
  const profile = useSearchProfile()
  const top = useJobs({ ...DEFAULT_FILTERS, sort: 'best' })
  const health = useHealth()
  const ai = useAiStatus()
  const decide = useDecide()
  const { find, score, finding, scoring } = useActions()
  const findElapsed = useElapsed(finding)
  const scoreElapsed = useElapsed(scoring)
  const [lastRun, setLastRun] = useState<LastRun | null>(() => readStored<LastRun>(LAST_RUN_KEY))
  const [showErrors, setShowErrors] = useState(false)

  const minScore = profile.data?.minimum_score ?? 80
  const best = useMemo(() => (top.data?.pages[0]?.items ?? []).filter((job) => job.score).slice(0, 3), [top.data])

  const stages: Stage[] | null = stats.data
    ? [
        { key: 'found', label: 'found', count: stats.data.found, color: 'rgb(163 185 178 / 0.42)', fraction: stats.data.found > 0 ? 1 : 0 },
        { key: 'relevant', label: 'relevant', count: stats.data.relevant, color: 'var(--color-apricot)', fraction: ratio(stats.data.relevant, stats.data.found) },
        { key: 'scored', label: 'scored', count: stats.data.analyzed, color: 'var(--color-jade)', fraction: ratio(stats.data.analyzed, stats.data.relevant) },
        { key: 'strong', label: 'strong fits', count: stats.data.high_fit, color: 'var(--color-mint)', fraction: ratio(stats.data.high_fit, stats.data.analyzed) },
      ]
    : null

  const text = stats.data ? headline(stats.data, minScore) : null
  const today = new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })

  const runFind = async () => {
    const run = await find()
    if (run) {
      setLastRun(run)
      setShowErrors(false)
    }
  }

  const lines = statusLines(health.data, ai.data, health.isError)

  return (
    <div className="space-y-20 md:space-y-28">
      <section className="grid items-center gap-14 lg:grid-cols-[minmax(0,1fr)_auto]">
        <div>
          <p className="text-lead text-mist">{today}</p>
          {text ? (
            <h1 className="text-display mt-5 [text-wrap:balance]">
              {text.before && `${text.before} `}
              {text.number !== null && (
                <>
                  <AnimatedNumber value={text.number} durationMs={1200} className="text-mint" />{' '}
                </>
              )}
              {text.after}
            </h1>
          ) : (
            <div className="mt-6 space-y-4" role="status" aria-label="Loading overview">
              <Bar className="h-16 w-4/5" />
              <Bar className="h-16 w-3/5" />
            </div>
          )}
          {text && <p className="mt-7 max-w-lg text-lead text-mist [text-wrap:pretty]">{text.sub}</p>}

          <div className="mt-10 flex flex-wrap items-center gap-3">
            <Button variant="primary" loading={finding} onClick={() => void runFind()}>
              {finding ? `Looking… ${findElapsed}s` : 'Find new jobs'}
            </Button>
            <Button loading={scoring} onClick={() => void score(5)}>
              {scoring ? `Scoring… ${scoreElapsed}s` : 'Score 5 jobs'}
            </Button>
          </div>
          {(finding || scoring) && (
            <p className="mt-4 text-label font-normal text-mist" aria-live="polite">
              {finding ? 'Checking every company in Sources. This can take a minute.' : 'Comparing each posting with your profile. This can take a minute.'}
            </p>
          )}
          {lastRun && !finding && (
            <div className="mt-6 text-mist">
              <p>
                Last search {relativeTime(lastRun.at)}: {lastRun.summary.new} new, {lastRun.summary.already_known + lastRun.summary.cross_source_duplicates} already known
                {lastRun.summary.errors.length > 0 && (
                  <>
                    ,{' '}
                    <button type="button" onClick={() => setShowErrors((v) => !v)} className="text-apricot underline decoration-apricot/40 underline-offset-4 transition hover:decoration-apricot">
                      {lastRun.summary.errors.length} {plural(lastRun.summary.errors.length, 'problem')}
                    </button>
                  </>
                )}
                .
              </p>
              {showErrors && (
                <ul className="mt-3 space-y-1.5 border-l-2 border-apricot/60 pl-5 text-label font-normal">
                  {lastRun.summary.errors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                  <li className="pt-1 text-fog">
                    <button type="button" onClick={() => navigate('/sources')} className="text-pearl underline underline-offset-4">
                      Fix company names in Sources
                    </button>
                  </li>
                </ul>
              )}
            </div>
          )}
        </div>

        <div className="justify-self-center">
          {stages && stats.data ? (
            <StageRings stages={stages} size={narrow ? 292 : 400} center={{ value: stats.data.high_fit, label: plural(stats.data.high_fit, 'strong fit') }} />
          ) : (
            <div className="shimmer rounded-full" style={{ width: narrow ? 292 : 400, height: narrow ? 292 : 400 }} aria-hidden="true" />
          )}
        </div>
      </section>

      {stats.data && stages && (
        <section aria-label="Pipeline">
          <dl className="grid grid-cols-2 gap-x-8 gap-y-10 md:grid-cols-4">
            {[
              { stage: stages[0], note: 'jobs seen across your sources' },
              { stage: stages[1], note: 'match your roles and rules' },
              { stage: stages[2], note: 'compared with your profile' },
              { stage: stages[3], note: `score ${minScore} or higher` },
            ].map(({ stage, note }) => (
              <div key={stage.key} className="border-t pt-5" style={{ borderColor: stage.color }}>
                <dt className="text-mist">{stage.label.charAt(0).toUpperCase() + stage.label.slice(1)}</dt>
                <dd>
                  <AnimatedNumber value={stage.count} durationMs={1100} className="text-title block text-pearl" />
                  <span className="text-label font-normal text-fog">{note}</span>
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <section>
        <div className="flex items-end justify-between gap-4">
          <h2 className="text-section">Best matches</h2>
          {best.length > 0 && (
            <Button variant="ghost" size="sm" onClick={() => navigate('/jobs')}>
              See all jobs
            </Button>
          )}
        </div>
        <div className="mt-4">
          {top.isPending ? null : best.length > 0 ? (
            <ul>
              {best.map((job) => (
                <JobRow key={job.id} job={job} onOpen={(id) => navigate(`/jobs?job=${id}`)} onDecision={decide} />
              ))}
            </ul>
          ) : (
            <EmptyState
              title="No scored jobs yet."
              action={
                <Button variant="primary" loading={scoring} onClick={() => void score(5)}>
                  Score 5 jobs
                </Button>
              }
            >
              Scores appear here, best first, once ApplyOS has compared jobs with your profile.
            </EmptyState>
          )}
        </div>
      </section>

      <section>
        <h2 className="text-section">Behind the scenes</h2>
        <ul className="mt-6 grid gap-x-10 gap-y-5 sm:grid-cols-2">
          {lines.map((line) => (
            <li key={line.label} className="flex gap-3">
              <span className="mt-[0.5rem] block size-2 shrink-0 rounded-full" style={{ background: line.ok ? 'var(--color-mint)' : 'var(--color-coral)' }} />
              <div>
                <div className="text-pearl">{line.label}</div>
                <div className="text-mist">{line.note}</div>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
