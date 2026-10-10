import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useActions } from '../../hooks/actions'
import { DURATION, EASE_OUT, SPRING } from '../../lib/motion'

interface Command {
  id: string
  label: string
  hint: string
  keywords: string
  run: () => void
}

/** Everything the app can do, reachable from the keyboard. Each entry does something real. */
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate()
  const { find, score } = useActions()
  const [query, setQuery] = useState('')
  const [cursor, setCursor] = useState(0)
  const input = useRef<HTMLInputElement>(null)

  const commands = useMemo<Command[]>(() => {
    const go = (path: string) => () => navigate(path)
    const base: Command[] = [
      { id: 'today', label: 'Go to Today', hint: 'Overview', keywords: 'home overview dashboard', run: go('/') },
      { id: 'jobs', label: 'Go to Jobs', hint: 'Ranked list', keywords: 'list feed', run: go('/jobs') },
      { id: 'sources', label: 'Go to Sources', hint: 'Companies and roles', keywords: 'settings search profile companies', run: go('/sources') },
      { id: 'find', label: 'Find new jobs', hint: 'Check every company in Sources', keywords: 'scan search discover fetch', run: () => void find() },
      { id: 'score', label: 'Score 5 jobs', hint: 'Best unscored first', keywords: 'analyze rate ai fit', run: () => void score(5) },
      { id: 'saved', label: 'Show saved jobs', hint: 'Jobs', keywords: 'bookmarks', run: go('/jobs?status=saved') },
      { id: 'strong', label: 'Show strong fits', hint: 'Score 80 or higher', keywords: 'best top high', run: go('/jobs?fit=80') },
      { id: 'unscored', label: 'Show jobs not scored yet', hint: 'Jobs', keywords: 'pending unrated', run: go('/jobs?fit=unscored') },
    ]
    const text = query.trim()
    if (text) {
      base.push({
        id: 'search',
        label: `Search jobs for "${text}"`,
        hint: 'Title or company',
        keywords: text.toLowerCase(),
        run: go(`/jobs?q=${encodeURIComponent(text)}`),
      })
    }
    return base
  }, [navigate, find, score, query])

  const visible = useMemo(() => {
    const text = query.trim().toLowerCase()
    if (!text) return commands.filter((c) => c.id !== 'search')
    return commands.filter((c) => c.id === 'search' || `${c.label} ${c.keywords}`.toLowerCase().includes(text))
  }, [commands, query])

  useEffect(() => {
    if (open) input.current?.focus()
  }, [open])

  const choose = (command: Command | undefined) => {
    if (!command) return
    onClose()
    setQuery('')
    setCursor(0)
    command.run()
  }

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setCursor((i) => Math.min(visible.length - 1, i + 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setCursor((i) => Math.max(0, i - 1))
    } else if (event.key === 'Enter') {
      event.preventDefault()
      choose(visible[Math.min(cursor, visible.length - 1)])
    } else if (event.key === 'Escape') {
      onClose()
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[60] flex items-start justify-center bg-spruce-950/55 px-4 pt-[14vh] backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, transition: { duration: DURATION.quick } }}
          onMouseDown={(event) => event.target === event.currentTarget && onClose()}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Commands"
            className="glass w-full max-w-xl overflow-hidden rounded-3xl"
            initial={{ opacity: 0, y: -12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1, transition: { duration: DURATION.base, ease: EASE_OUT } }}
            exit={{ opacity: 0, y: -8, transition: { duration: DURATION.quick } }}
          >
            <input
              ref={input}
              value={query}
              onChange={(event) => {
                setQuery(event.target.value)
                setCursor(0)
              }}
              onKeyDown={onKeyDown}
              placeholder="Type a command, or search jobs"
              aria-label="Command"
              className="w-full bg-transparent px-6 py-5 text-lead text-pearl outline-none placeholder:text-fog"
            />
            <ul className="max-h-[50vh] overflow-y-auto border-t border-white/10 p-2" role="listbox">
              {visible.map((command, index) => (
                <li key={command.id} role="option" aria-selected={index === cursor}>
                  <button
                    type="button"
                    onMouseMove={() => setCursor(index)}
                    onClick={() => choose(command)}
                    className="relative flex w-full items-baseline justify-between gap-4 rounded-2xl px-4 py-3 text-left"
                  >
                    {index === cursor && (
                      <motion.span layoutId="palette-cursor" transition={SPRING} className="absolute inset-0 rounded-2xl bg-white/[0.09]" aria-hidden="true" />
                    )}
                    <span className="relative text-pearl">{command.label}</span>
                    <span className="relative text-label font-normal text-mist">{command.hint}</span>
                  </button>
                </li>
              ))}
              {visible.length === 0 && <li className="px-4 py-6 text-mist">Nothing matches. Try a job title or company name.</li>}
            </ul>
            <div className="border-t border-white/10 px-6 py-3 text-label font-normal text-fog">Up and down to move, Enter to run, Esc to close</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
