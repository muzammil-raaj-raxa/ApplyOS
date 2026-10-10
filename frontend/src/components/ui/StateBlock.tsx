import type { ReactNode } from 'react'
import { describeError } from '../../lib/errors'
import { Button } from './Button'

/** Empty means: here is what to do next. Errors say what happened and how to fix it. */
export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="max-w-xl py-16">
      <h2 className="text-title text-pearl">{title}</h2>
      {children && <p className="mt-4 text-lead text-mist">{children}</p>}
      {action && <div className="mt-8 flex flex-wrap gap-3">{action}</div>}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { title, body } = describeError(error)
  return (
    <div role="alert" className="max-w-xl py-16">
      <h2 className="text-title text-pearl">{title}</h2>
      <p className="mt-4 text-lead text-coral">{body}</p>
      {onRetry && (
        <div className="mt-8">
          <Button onClick={onRetry}>Try again</Button>
        </div>
      )}
    </div>
  )
}
