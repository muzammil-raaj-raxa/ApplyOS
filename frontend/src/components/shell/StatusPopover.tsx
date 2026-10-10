import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { useAiStatus, useHealth } from '../../hooks/queries'
import { DURATION, EASE_OUT } from '../../lib/motion'
import { LEVEL_COLOR, statusLines, systemLevel } from '../../lib/status'

export function StatusOrb() {
  const [open, setOpen] = useState(false)
  const health = useHealth()
  const ai = useAiStatus()
  const box = useRef<HTMLDivElement>(null)
  const level = systemLevel(health.data, health.isError)

  useEffect(() => {
    if (!open) return
    const onDown = (event: MouseEvent) => {
      if (!box.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const lines = statusLines(health.data, ai.data, health.isError)

  return (
    <div ref={box} className="relative">
      <button
        type="button"
        aria-label="System status"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="grid size-11 place-items-center rounded-full transition hover:bg-white/[0.08]"
      >
        <span
          className="block size-2.5 rounded-full"
          style={{ background: LEVEL_COLOR[level], boxShadow: `0 0 12px ${LEVEL_COLOR[level]}` }}
        />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1, transition: { duration: DURATION.base, ease: EASE_OUT } }}
            exit={{ opacity: 0, y: 6, transition: { duration: DURATION.quick } }}
            className="glass absolute right-0 bottom-[calc(100%+0.75rem)] w-[min(21rem,calc(100vw-2rem))] origin-bottom-right rounded-3xl p-5"
            role="dialog"
            aria-label="System status"
          >
            <p className="text-heading">{level === 'good' ? 'Everything is running' : level === 'warn' ? 'Running, with one thing to fix' : 'Needs attention'}</p>
            <ul className="mt-4 space-y-3.5">
              {lines.map((line) => (
                <li key={line.label} className="flex gap-3">
                  <span className="mt-[0.45rem] block size-2 shrink-0 rounded-full" style={{ background: line.ok ? 'var(--color-mint)' : 'var(--color-coral)' }} />
                  <div>
                    <div className="text-label text-pearl">{line.label}</div>
                    <div className="text-label font-normal text-mist">{line.note}</div>
                  </div>
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
