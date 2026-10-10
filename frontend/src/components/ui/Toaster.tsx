import { AnimatePresence, motion } from 'motion/react'
import { useCallback, useRef, useState, type ReactNode } from 'react'
import { DURATION, EASE_OUT } from '../../lib/motion'
import { ToastContext, type ToastInput } from './toast-context'

interface Toast extends ToastInput {
  id: number
}

/** Confirmations reuse the verb of the action ("Saved"), and offer undo where undo exists. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => setToasts((list) => list.filter((t) => t.id !== id)), [])

  const push = useCallback(
    (toast: ToastInput) => {
      const id = nextId.current++
      setToasts((list) => [...list.slice(-2), { ...toast, id }])
      window.setTimeout(() => dismiss(id), toast.action ? 8000 : 5000)
    },
    [dismiss],
  )

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-[calc(6.5rem+env(safe-area-inset-bottom))] z-[80] flex flex-col items-center gap-2 px-4"
        role="status"
        aria-live="polite"
      >
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              layout
              initial={{ opacity: 0, y: 14, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1, transition: { duration: DURATION.base, ease: EASE_OUT } }}
              exit={{ opacity: 0, scale: 0.97, transition: { duration: DURATION.quick } }}
              className={`glass pointer-events-auto flex max-w-[min(32rem,100%)] items-center gap-4 rounded-full py-2.5 pr-3 pl-5 text-label ${toast.tone === 'error' ? 'text-coral' : 'text-pearl'}`}
            >
              <span>{toast.message}</span>
              {toast.action && (
                <button
                  type="button"
                  onClick={() => {
                    toast.action?.onClick()
                    dismiss(toast.id)
                  }}
                  className="rounded-full bg-white/10 px-3 py-1 font-semibold text-pearl transition hover:bg-white/20"
                >
                  {toast.action.label}
                </button>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}
