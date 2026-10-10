import { useEffect, useState } from 'react'

/** Whole seconds since `active` turned true. Shows that a long action is still alive. */
export function useElapsed(active: boolean): number {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    if (!active) return
    const started = Date.now()
    const id = window.setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 1000)
    return () => {
      window.clearInterval(id)
      setSeconds(0)
    }
  }, [active])
  return active ? seconds : 0
}
