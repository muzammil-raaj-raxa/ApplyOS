import { motion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useDecide } from '../../hooks/decisions'
import { useIsNarrow } from '../../hooks/useMedia'
import { useJob, useScoreJob } from '../../hooks/queries'
import { bandFor, formatSalary, plural, RECOMMENDATION_TEXT, relativeTime, sourceName, WORKPLACE_TEXT } from '../../lib/format'
import { DURATION, EASE_OUT, SPRING } from '../../lib/motion'
import type { Job } from '../../lib/types'
import { Button } from '../ui/Button'
import { BookmarkIcon, ChevronIcon, CloseIcon, ExternalIcon } from '../ui/icons'
import { Bar } from '../ui/Skeleton'
import { describeError } from '../../lib/errors'
import { ErrorState } from '../ui/StateBlock'
import { useToast } from '../ui/toast-context'
import { FitRing } from '../viz/FitRing'
import { DimensionList } from './DimensionList'

interface DossierProps {
  jobId: number
  onClose: () => void
  onStep: (direction: -1 | 1) => void
  canStep: { prev: boolean; next: boolean }
}

const SPONSORSHIP_TEXT: Record<string, string> = {
  available: 'Offered',
  not_available: 'Not offered, or you must already be authorized',
  unknown: 'Not mentioned',
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="text-heading text-pearl">{title}</h3>
      <div className="mt-4">{children}</div>
    </section>
  )
}

function Pill({ children, tone }: { children: React.ReactNode; tone: 'have' | 'miss' | 'plain' }) {
  const styles = {
    have: 'bg-white/[0.07] text-pearl ring-white/10',
    miss: 'bg-clay/[0.08] text-clay ring-clay/30',
    plain: 'bg-white/[0.05] text-mist ring-white/10',
  }[tone]
  return <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-label ring-1 ${styles}`}>{tone === 'have' && <span className="size-1.5 rounded-full bg-mint" />}{children}</span>
}

function Facts({ job }: { job: Job }) {
  const salary = formatSalary(job.salary_min, job.salary_max, job.salary_currency)
  const rows: [string, string | null][] = [
    ['Workplace', job.workplace ? WORKPLACE_TEXT[job.workplace] : null],
    ['Location', job.location],
    ['Salary', salary],
    ['Experience asked', job.minimum_years ? `${job.minimum_years}+ ${plural(job.minimum_years, 'year')}` : 'Not stated'],
    ['Visa sponsorship', job.sponsorship ? (SPONSORSHIP_TEXT[job.sponsorship] ?? job.sponsorship) : null],
    ['Employment', job.employment_type],
    ['Found on', sourceName(job.source)],
  ]
  return (
    <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-8 gap-y-2.5">
      {rows
        .filter(([, value]) => value)
        .map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-fog">{label}</dt>
            <dd className="text-pearl">{value}</dd>
          </div>
        ))}
    </dl>
  )
}

function DossierBody({ job, onClose, onStep, canStep }: { job: Job } & Omit<DossierProps, 'jobId'>) {
  const decide = useDecide()
  const scoreJob = useScoreJob()
  const toast = useToast()
  const [expanded, setExpanded] = useState(false)

  const score = job.score
  const analysis = job.analysis
  const scoringThis = scoreJob.isPending && scoreJob.variables?.id === job.id
  const saved = job.user_decision === 'SAVED'
  const rejected = job.user_decision === 'REJECTED'
  const band = score ? bandFor(score.overall_score) : null

  const runScore = async (force: boolean) => {
    try {
      const result = await scoreJob.mutateAsync({ id: job.id, force })
      toast({ message: `Scored ${result.analysis.overall_score}. ${bandFor(result.analysis.overall_score).label}.` })
    } catch {
      // the error is shown inline below
    }
  }

  const scoreError = scoreJob.error ? describeError(scoreJob.error) : null

  return (
    <>
      <div className="flex items-center justify-between gap-2 p-4 pb-0 md:p-5 md:pb-0">
        <Button variant="ghost" size="icon" aria-label="Close" onClick={onClose} autoFocus>
          <CloseIcon />
        </Button>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" aria-label="Previous job" disabled={!canStep.prev} onClick={() => onStep(-1)}>
            <ChevronIcon className="rotate-180" />
          </Button>
          <Button variant="ghost" size="icon" aria-label="Next job" disabled={!canStep.next} onClick={() => onStep(1)}>
            <ChevronIcon />
          </Button>
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer noopener"
            className="ml-1 inline-flex h-9 items-center gap-2 rounded-control px-3.5 text-label text-mist transition hover:bg-white/[0.07] hover:text-pearl"
          >
            Open posting
            <ExternalIcon width={16} height={16} />
          </a>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto overscroll-contain px-6 pt-6 pb-10 md:px-9">
        <motion.div key={job.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE_OUT } }} className="space-y-11">
          <header>
            <h2 className="text-title text-pearl [text-wrap:balance]">{job.title}</h2>
            <p className="mt-3 text-lead text-mist">
              <span className="font-semibold text-pearl">{job.company}</span>
              {job.location ? `, ${job.location}` : ''}
            </p>
            {job.user_decision && (
              <p className="mt-3 text-label" style={{ color: saved ? 'var(--color-mint)' : 'var(--color-coral)' }}>
                {saved ? 'Saved' : 'Rejected'}
              </p>
            )}
          </header>

          {job.relevant === false && (
            <div className="border-l-2 border-coral/60 pl-5">
              <p className="font-semibold text-pearl">Filtered out before scoring</p>
              <ul className="mt-1.5 space-y-1 text-mist">
                {job.filter_reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </div>
          )}

          {score && analysis && band ? (
            <>
              <section className="flex flex-col items-start gap-7 sm:flex-row sm:items-center">
                <FitRing score={score.overall_score} parts={score} size={176} animate showBand />
                <div className="min-w-0">
                  <p className="text-heading text-pearl">{RECOMMENDATION_TEXT[analysis.recommendation]}</p>
                  <p className="mt-3 text-mist [text-wrap:pretty]">{analysis.summary}</p>
                </div>
              </section>

              <Section title="How the score is built">
                <p className="mb-5 text-mist">
                  Each arc of the ring is one of these. Longer arcs count for more, and fuller arcs scored higher.
                </p>
                <DimensionList score={score} />
              </Section>

              <Section title="Skills">
                <div className="space-y-5">
                  <div>
                    <p className="mb-2.5 text-label text-fog">You cover</p>
                    <div className="flex flex-wrap gap-2">
                      {analysis.skill_coverage.covered.length ? analysis.skill_coverage.covered.map((s) => <Pill key={s} tone="have">{s}</Pill>) : <span className="text-mist">None of the required technologies detected in the posting.</span>}
                    </div>
                  </div>
                  {analysis.skill_coverage.missing.length > 0 && (
                    <div>
                      <p className="mb-2.5 text-label text-fog">Required, but not in your profile</p>
                      <div className="flex flex-wrap gap-2">
                        {analysis.skill_coverage.missing.map((s) => (
                          <Pill key={s} tone="miss">{s}</Pill>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </Section>

              {analysis.confirmed_matches.length > 0 && (
                <Section title="Where you match">
                  <ul className="space-y-4">
                    {analysis.confirmed_matches.map((m) => (
                      <li key={`${m.requirement}-${m.evidence_ref}`}>
                        <p className="text-pearl">{m.requirement}</p>
                        <p className="mt-1 text-mist">
                          <span className="mr-2 rounded-full bg-white/[0.08] px-2.5 py-0.5 text-label text-pearl">{m.evidence_ref}</span>
                          {m.evidence}
                        </p>
                      </li>
                    ))}
                  </ul>
                </Section>
              )}

              {analysis.partial_matches.length > 0 && (
                <Section title="Partly there">
                  <ul className="space-y-4">
                    {analysis.partial_matches.map((m) => (
                      <li key={`${m.requirement}-${m.evidence_ref}`}>
                        <p className="text-pearl">{m.requirement}</p>
                        <p className="mt-1 text-mist">
                          <span className="mr-2 rounded-full bg-white/[0.08] px-2.5 py-0.5 text-label text-pearl">{m.evidence_ref}</span>
                          {m.note}
                        </p>
                      </li>
                    ))}
                  </ul>
                </Section>
              )}

              {analysis.gaps.length > 0 && (
                <Section title="Gaps the AI found">
                  <ul className="space-y-2 text-mist">
                    {analysis.gaps.map((gap) => (
                      <li key={gap}>{gap}</li>
                    ))}
                  </ul>
                </Section>
              )}

              {(analysis.risks.length > 0 || analysis.uncertain_requirements.length > 0) && (
                <Section title="Worth knowing">
                  <ul className="space-y-3">
                    {analysis.risks.map((risk) => (
                      <li key={risk} className="border-l-2 border-apricot/70 pl-5 text-pearl/90">{risk}</li>
                    ))}
                    {analysis.uncertain_requirements.map((item) => (
                      <li key={item} className="border-l-2 border-white/20 pl-5 text-mist">Unclear: {item}</li>
                    ))}
                  </ul>
                </Section>
              )}
            </>
          ) : (
            <section className="flex flex-col items-start gap-7 sm:flex-row sm:items-center">
              <FitRing score={null} size={120} working={scoringThis} />
              <div>
                <p className="text-heading text-pearl">{scoringThis ? 'Scoring this job…' : 'This job has not been scored yet'}</p>
                <p className="mt-2 max-w-md text-mist">
                  {job.analysis_status === 'needs_review'
                    ? `The AI's last answer failed its checks, so nothing was saved. ${job.analysis_error ?? ''}`
                    : 'ApplyOS compares the posting with your verified profile and shows exactly why it fits or does not. It can take up to a minute.'}
                </p>
                <div className="mt-5">
                  <Button variant="primary" loading={scoringThis} onClick={() => runScore(job.analysis_status === 'needs_review')}>
                    {job.analysis_status === 'needs_review' ? 'Try scoring again' : 'Score this job'}
                  </Button>
                </div>
              </div>
            </section>
          )}

          {scoreError && (
            <div role="alert" className="border-l-2 border-coral pl-5">
              <p className="font-semibold text-pearl">{scoreError.title}</p>
              <p className="mt-1 text-coral">{scoreError.body}</p>
            </div>
          )}

          <Section title="About the posting">
            <Facts job={job} />
          </Section>

          {(job.required_skills.length > 0 || job.preferred_skills.length > 0) && (
            <Section title="Technologies in the posting">
              <div className="flex flex-wrap gap-2">
                {job.required_skills.map((s) => <Pill key={s} tone="plain">{s}</Pill>)}
                {job.preferred_skills.map((s) => (
                  <span key={s} className="inline-flex rounded-full px-3 py-1 text-label text-fog ring-1 ring-dashed ring-white/15">{s} (nice to have)</span>
                ))}
              </div>
            </Section>
          )}

          {job.description && (
            <Section title="The posting">
              <div className="relative">
                <p className={`whitespace-pre-line text-mist [overflow-wrap:anywhere] ${expanded ? '' : 'max-h-44 overflow-hidden'}`}>{job.description}</p>
                {!expanded && <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-[#0f2a25] to-transparent" />}
              </div>
              <Button variant="ghost" size="sm" className="mt-3 -ml-3.5" onClick={() => setExpanded((v) => !v)}>
                {expanded ? 'Show less' : 'Read the full posting'}
              </Button>
            </Section>
          )}

          {score && (
            <p className="text-label font-normal text-fog">
              Scored {relativeTime(score.analyzed_at)} by {score.model} using {score.prompt_version}.
            </p>
          )}
        </motion.div>
      </div>

      <div className="flex items-center gap-2 border-t border-white/10 px-4 py-3.5 md:px-7">
        {rejected ? (
          <Button variant="secondary" onClick={() => decide(job.id, 'clear', job.user_decision)}>
            Restore to list
          </Button>
        ) : (
          <>
            <Button variant={saved ? 'secondary' : 'primary'} icon={<BookmarkIcon filled={saved} width={18} height={18} />} onClick={() => decide(job.id, saved ? 'clear' : 'save', job.user_decision)}>
              {saved ? 'Saved' : 'Save'}
            </Button>
            <Button variant="danger" onClick={() => decide(job.id, 'reject', job.user_decision)}>
              Reject
            </Button>
          </>
        )}
        <div className="flex-1" />
        {score && (
          <Button variant="ghost" loading={scoringThis} onClick={() => runScore(true)}>
            Score again
          </Button>
        )}
      </div>
    </>
  )
}

/** The full story of one job. It slides over the list so you never lose your place. */
export function Dossier({ jobId, onClose, onStep, canStep }: DossierProps) {
  const narrow = useIsNarrow()
  const { data: job, error, refetch } = useJob(jobId)
  const opener = useRef<Element | null>(document.activeElement)

  useEffect(() => {
    const element = opener.current
    return () => {
      if (element instanceof HTMLElement) element.focus()
    }
  }, [])

  const hidden = narrow ? { y: '100%', opacity: 1 } : { x: 56, opacity: 0 }
  const shown = narrow ? { y: 0, opacity: 1 } : { x: 0, opacity: 1 }

  return createPortal(
    <>
      <motion.div
        className="fixed inset-0 z-40 bg-spruce-950/60 backdrop-blur-[3px]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0, transition: { duration: DURATION.quick } }}
        onClick={onClose}
        aria-hidden="true"
      />
      <motion.aside
        role="dialog"
        aria-modal="true"
        aria-label={job ? `${job.title} at ${job.company}` : 'Job details'}
        className="glass fixed inset-x-0 bottom-0 top-10 z-50 flex flex-col rounded-t-[1.75rem] md:inset-y-3 md:right-3 md:left-auto md:w-[min(40rem,calc(100vw-1.5rem))] md:rounded-[1.75rem]"
        style={{ background: 'linear-gradient(180deg, rgb(20 52 46 / 0.86), rgb(10 31 27 / 0.92))' }}
        initial={hidden}
        animate={shown}
        exit={{ ...hidden, transition: { duration: DURATION.base, ease: EASE_OUT } }}
        transition={SPRING}
      >
        {job ? (
          <DossierBody job={job} onClose={onClose} onStep={onStep} canStep={canStep} />
        ) : error ? (
          <div className="p-8">
            <ErrorState error={error} onRetry={() => void refetch()} />
          </div>
        ) : (
          <div className="space-y-5 p-8" role="status" aria-label="Loading job">
            <Bar className="h-9 w-3/4" />
            <Bar className="h-5 w-1/2" />
            <Bar className="mt-8 h-40 w-full" />
          </div>
        )}
      </motion.aside>
    </>,
    document.body,
  )
}

