import { AnimatePresence, motion } from 'motion/react'
import { useId, useState } from 'react'
import { DURATION, EASE_OUT } from '../../lib/motion'
import { CloseIcon } from '../ui/icons'

interface TagEditorProps {
  label: string
  hint?: string
  values: string[]
  onChange: (values: string[]) => void
  placeholder?: string
  validate?: (value: string) => string | null
}

/** Type, press Enter or comma, and it becomes a chip. Backspace removes the last one. */
export function TagEditor({ label, hint, values, onChange, placeholder = 'Add one and press Enter', validate }: TagEditorProps) {
  const [draft, setDraft] = useState('')
  const [error, setError] = useState<string | null>(null)
  const id = useId()

  const commit = (raw: string) => {
    const value = raw.trim().replace(/,+$/, '').trim()
    if (!value) return
    if (values.some((existing) => existing.toLowerCase() === value.toLowerCase())) {
      setError(`"${value}" is already in the list.`)
      return
    }
    const problem = validate?.(value) ?? null
    if (problem) {
      setError(problem)
      return
    }
    onChange([...values, value])
    setDraft('')
    setError(null)
  }

  return (
    <div>
      <label htmlFor={id} className="block text-heading text-pearl">
        {label}
      </label>
      {hint && <p className="mt-1 text-mist">{hint}</p>}
      <div className="mt-3 flex flex-wrap items-center gap-2 rounded-2xl bg-white/[0.04] p-2.5 ring-1 ring-white/[0.08] transition focus-within:bg-white/[0.06] focus-within:ring-2 focus-within:ring-mint/60 hover:ring-white/20">
        <AnimatePresence initial={false}>
          {values.map((value) => (
            <motion.span
              key={value}
              layout
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1, transition: { duration: DURATION.base, ease: EASE_OUT } }}
              exit={{ opacity: 0, scale: 0.9, transition: { duration: DURATION.quick } }}
              className="inline-flex items-center gap-1.5 rounded-full bg-white/[0.09] py-1 pr-1.5 pl-3.5 text-pearl"
            >
              {value}
              <button
                type="button"
                aria-label={`Remove ${value}`}
                onClick={() => onChange(values.filter((v) => v !== value))}
                className="grid size-6 place-items-center rounded-full text-mist transition hover:bg-white/15 hover:text-pearl"
              >
                <CloseIcon width={14} height={14} />
              </button>
            </motion.span>
          ))}
        </AnimatePresence>
        <input
          id={id}
          value={draft}
          onChange={(event) => {
            setDraft(event.target.value)
            if (error) setError(null)
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ',') {
              event.preventDefault()
              commit(draft)
            } else if (event.key === 'Backspace' && !draft && values.length) {
              onChange(values.slice(0, -1))
            }
          }}
          onBlur={() => commit(draft)}
          placeholder={values.length ? '' : placeholder}
          className="min-w-[10rem] flex-1 bg-transparent px-2 py-1.5 text-pearl outline-none placeholder:text-fog"
        />
      </div>
      {error && (
        <p role="alert" className="mt-2 text-label text-coral">
          {error}
        </p>
      )}
    </div>
  )
}
