import { useEffect, useRef, useState } from 'react'
import { usePrefersReducedMotion } from './useMedia'

const easeOutExpo = (t: number) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t))

/** Counts from the previous value to the new one. Reduced motion shows the value at once. */
export function useCountUp(target: number, durationMs = 900, from = 0): number {
  const reduced = usePrefersReducedMotion()
  const [shown, setShown] = useState(from)
  const current = useRef(from)

  useEffect(() => {
    if (reduced) return
    const start = current.current
    if (start === target) return
    const begin = performance.now()
    let frame = 0
    const tick = (now: number) => {
      const progress = Math.min(1, (now - begin) / durationMs)
      const value = start + (target - start) * easeOutExpo(progress)
      current.current = value
      setShown(value)
      if (progress < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target, durationMs, reduced])

  return reduced ? target : shown
}
