import { useCountUp } from '../../hooks/useCountUp'

/** A number that travels to its new value. Reserve it for numbers that mean something. */
export function AnimatedNumber({ value, durationMs = 900, from = 0, className }: { value: number; durationMs?: number; from?: number; className?: string }) {
  const shown = useCountUp(value, durationMs, from)
  return (
    <span className={`tnum ${className ?? ''}`} aria-label={String(value)}>
      <span aria-hidden="true">{Math.round(shown)}</span>
    </span>
  )
}
