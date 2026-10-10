import { useIsFetching, useIsMutating } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'
import { useDebounced } from '../../hooks/useDebounced'

/** A hairline across the top that is lit only while the system is talking to the backend. */
export function ActivityLine() {
  const fetching = useIsFetching({ predicate: (q) => q.queryKey[0] !== 'health' && q.queryKey[0] !== 'ai-status' })
  const mutating = useIsMutating()
  const busy = useDebounced(fetching + mutating > 0, 200)

  return (
    <AnimatePresence>
      {busy && (
        <motion.div
          key="activity"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
          className="pointer-events-none fixed inset-x-0 top-0 z-[70] h-[2px] overflow-hidden bg-white/[0.06]"
          role="progressbar"
          aria-label="Working"
        >
          <div className="h-full w-2/5 animate-sweep bg-gradient-to-r from-transparent via-mint to-transparent" />
        </motion.div>
      )}
    </AnimatePresence>
  )
}
