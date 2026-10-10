import { motion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { formatSalary, sourceName, WORKPLACE_TEXT } from '../../lib/format'
import { bandFor } from '../../lib/format'
import { DURATION, EASE_OUT, SPRING } from '../../lib/motion'
import type { Job } from '../../lib/types'
import { FitRing } from '../viz/FitRing'
import { Button } from '../ui/Button'
import { BookmarkIcon, CloseIcon } from '../ui/icons'

interface JobRowProps {
  job: Job
  selected?: boolean
  /** The id used for the rule that glides between selected rows. Omit to disable it. */
  ruleId?: string
  scoring?: boolean
  onOpen: (id: number) => void
  onDecision: (id: number, decision: 'save' | 'reject' | 'clear') => void
  onScore?: (id: number) => void
}

function listFew(items: string[], max = 4): string {
  return items.length > max ? `${items.slice(0, max).join(', ')} and ${items.length - max} more` : items.join(', ')
}

export function JobRow({ job, selected = false, ruleId, scoring = false, onOpen, onDecision, onScore }: JobRowProps) {
  const score = job.score
  const rejected = job.user_decision === 'REJECTED'
  const saved = job.user_decision === 'SAVED'

  // Draw the ring in only when a score arrives while you are looking at the row.
  const previous = useRef(score?.overall_score ?? null)
  const [justScored, setJustScored] = useState(false)
  useEffect(() => {
    const now = score?.overall_score ?? null
    if (previous.current === null && now !== null) setJustScored(true)
    previous.current = now
  }, [score?.overall_score])

  const salary = formatSalary(job.salary_min, job.salary_max, job.salary_currency)
  const place = job.workplace && job.workplace !== 'unknown' ? WORKPLACE_TEXT[job.workplace] : null
  const where = place && job.location && job.location.toLowerCase().includes(place.toLowerCase()) ? job.location : [place, job.location].filter(Boolean).join(', ')

  const reveal = 'transition-opacity duration-150 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 [@media(hover:none)]:opacity-100'

  return (
    <motion.li
      layout="position"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1, transition: { duration: DURATION.base, ease: EASE_OUT } }}
      exit={{ opacity: 0, height: 0, transition: { duration: DURATION.base, ease: EASE_OUT } }}
      transition={SPRING}
      className="group relative list-none overflow-hidden border-b border-[var(--hairline)]"
    >
      {selected && ruleId && (
        <motion.span
          layoutId={ruleId}
          transition={SPRING}
          className="absolute top-5 bottom-5 left-0 w-[3px] rounded-full"
          style={{ background: score ? bandFor(score.overall_score).color : 'var(--color-mist)' }}
          aria-hidden="true"
        />
      )}
      <div className={`flex items-center gap-2 py-5 transition-opacity ${rejected ? 'opacity-55' : ''}`}>
        <button
          type="button"
          onClick={() => onOpen(job.id)}
          aria-label={`Open ${job.title} at ${job.company}`}
          className="flex min-w-0 flex-1 items-center gap-4 rounded-2xl text-left sm:gap-5 md:pl-3"
        >
          <span className="transition-transform duration-200 ease-out-expo group-hover:scale-[1.06]">
            <FitRing
              score={score?.overall_score ?? null}
              parts={score}
              size={60}
              animate={justScored}
              working={scoring}
            />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-heading text-pearl [text-wrap:balance]">{job.title}</span>
            <span className="mt-1 flex flex-wrap items-baseline gap-x-4 gap-y-0.5 text-mist">
              <span className="font-semibold text-pearl/80">{job.company}</span>
              {where && <span>{where}</span>}
              {salary && <span className="tnum">{salary}</span>}
              <span className="text-fog">{sourceName(job.source)}</span>
            </span>
            <span className="mt-2 block text-label font-normal">
              {score ? (
                <>
                  {score.matched.length > 0 && (
                    <span className="text-mist">
                      <span className="text-fog">Covers </span>
                      {listFew(score.matched)}
                    </span>
                  )}
                  {(() => {
                    const missing = score.gaps.length ? score.gaps : []
                    return missing.length > 0 ? (
                      <span className="ml-4 inline-block text-clay">
                        <span className="text-clay/60">Gaps </span>
                        {listFew(missing, 2)}
                      </span>
                    ) : null
                  })()}
                </>
              ) : job.analysis_status === 'needs_review' ? (
                <span className="text-apricot">The AI's answer failed its checks. Open to review.</span>
              ) : job.relevant === false && job.filter_reasons.length > 0 ? (
                <span className="text-coral/80">Filtered out: {job.filter_reasons[0]}</span>
              ) : (
                <span className="text-fog">{scoring ? 'Scoring now…' : 'Not scored yet'}</span>
              )}
            </span>
          </span>
        </button>

        <div className="flex shrink-0 items-center gap-0.5">
          {rejected ? (
            <Button variant="ghost" size="sm" onClick={() => onDecision(job.id, 'clear')}>
              Restore
            </Button>
          ) : (
            <>
              {!score && onScore && (
                <Button variant="ghost" size="sm" loading={scoring} onClick={() => onScore(job.id)} className={scoring ? '' : reveal}>
                  Score
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon"
                aria-label={saved ? `Remove ${job.title} from saved` : `Save ${job.title}`}
                aria-pressed={saved}
                onClick={() => onDecision(job.id, saved ? 'clear' : 'save')}
                className={`${saved ? '!text-mint' : `${reveal}`}`}
              >
                <BookmarkIcon filled={saved} />
              </Button>
              <Button variant="ghost" size="icon" aria-label={`Reject ${job.title}`} onClick={() => onDecision(job.id, 'reject')} className={`hover:!text-coral ${reveal}`}>
                <CloseIcon />
              </Button>
            </>
          )}
        </div>
      </div>
    </motion.li>
  )
}
