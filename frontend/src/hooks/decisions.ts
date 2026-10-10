import { describeError } from '../lib/errors'
import { useToast } from '../components/ui/toast-context'
import type { Decision } from '../lib/types'
import { useDecision } from './queries'

/** Save, reject and restore, with a confirmation that offers undo. */
export function useDecide() {
  const mutation = useDecision()
  const toast = useToast()

  return (id: number, decision: 'save' | 'reject' | 'clear', previous: Decision = null) => {
    mutation.mutate(
      { id, decision },
      {
        onSuccess: () => {
          const undo = {
            label: 'Undo',
            onClick: () => mutation.mutate({ id, decision: previous === 'SAVED' ? 'save' : previous === 'REJECTED' ? 'reject' : 'clear' }),
          }
          if (decision === 'save') toast({ message: 'Saved.', action: undo })
          else if (decision === 'reject') toast({ message: 'Rejected. It will not show in your list.', action: undo })
          else toast({ message: previous === 'REJECTED' ? 'Restored to your list.' : 'Removed from saved.' })
        },
        onError: (error) => toast({ message: describeError(error).body, tone: 'error' }),
      },
    )
  }
}
