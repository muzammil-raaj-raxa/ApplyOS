import { motion } from 'motion/react'
import { SPRING } from '../../lib/motion'

interface Option<T extends string> {
  value: T
  label: string
}

interface SegmentedProps<T extends string> {
  label: string
  value: T
  options: Option<T>[]
  onChange: (value: T) => void
  /** Must be unique per control on the page: the highlight glides between options. */
  id: string
}

export function Segmented<T extends string>({ label, value, options, onChange, id }: SegmentedProps<T>) {
  return (
    <div role="group" aria-label={label} className="inline-flex shrink-0 rounded-full bg-white/[0.045] p-1 ring-1 ring-white/[0.07]">
      {options.map((option) => {
        const active = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            className={`relative rounded-full px-3.5 py-1.5 text-label transition-colors duration-150 ${active ? 'text-spruce-900' : 'text-mist hover:text-pearl'}`}
          >
            {active && (
              <motion.span
                layoutId={`seg-${id}`}
                transition={SPRING}
                className="absolute inset-0 rounded-full bg-pearl"
                aria-hidden="true"
              />
            )}
            <span className="relative">{option.label}</span>
          </button>
        )
      })}
    </div>
  )
}
