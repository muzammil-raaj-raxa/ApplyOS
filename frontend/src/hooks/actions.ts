import { describeError } from '../lib/errors'
import { useToast } from '../components/ui/toast-context'
import { plural } from '../lib/format'
import { writeStored } from '../lib/storage'
import type { BatchSummary, DiscoverySummary } from '../lib/types'
import { useFindJobs, useScoreJobs } from './queries'

export const LAST_RUN_KEY = 'applyos:last-find'

export interface LastRun {
  at: string
  summary: DiscoverySummary
}

export function describeFind(summary: DiscoverySummary): string {
  const found = `Found ${summary.new} new ${plural(summary.new, 'job')}`
  return summary.errors.length ? `${found}. ${summary.errors.length} ${plural(summary.errors.length, 'source had a problem', 'sources had problems')}.` : `${found}.`
}

export function describeScore(batch: BatchSummary): string {
  if (batch.stopped_reason && batch.analyzed === 0) return `Scoring stopped: ${batch.stopped_reason}`
  if (batch.analyzed === 0 && batch.needs_review === 0) return 'No unscored jobs to score.'
  const parts = [`Scored ${batch.analyzed} ${plural(batch.analyzed, 'job')}`]
  if (batch.needs_review) parts.push(`${batch.needs_review} need your review`)
  if (batch.stopped_reason) parts.push('stopped early, no AI available')
  return `${parts.join(', ')}.`
}

/** The two long-running actions, shared by the Today page and the command palette. */
export function useActions() {
  const findMutation = useFindJobs()
  const scoreMutation = useScoreJobs()
  const toast = useToast()

  const find = async (): Promise<LastRun | null> => {
    try {
      const summary = await findMutation.mutateAsync()
      const run = { at: new Date().toISOString(), summary }
      writeStored(LAST_RUN_KEY, run)
      toast({ message: describeFind(summary) })
      return run
    } catch (error) {
      toast({ message: describeError(error).body, tone: 'error' })
      return null
    }
  }

  const score = async (limit = 5): Promise<BatchSummary | null> => {
    try {
      const batch = await scoreMutation.mutateAsync(limit)
      toast({ message: describeScore(batch), tone: batch.analyzed === 0 && batch.stopped_reason ? 'error' : 'default' })
      return batch
    } catch (error) {
      toast({ message: describeError(error).body, tone: 'error' })
      return null
    }
  }

  return { find, score, finding: findMutation.isPending, scoring: scoreMutation.isPending }
}
