import { AnimatePresence, MotionConfig, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { useLocation, useOutlet } from 'react-router-dom'
import { PAGE_TRANSITION } from '../../lib/motion'
import { ActivityLine } from './ActivityLine'
import { CommandPalette } from './CommandPalette'
import { Dock } from './Dock'
import { Wordmark } from './Wordmark'

export function Shell() {
  const location = useLocation()
  const outlet = useOutlet()
  const [palette, setPalette] = useState(false)

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPalette((open) => !open)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <MotionConfig reducedMotion="user">
      <ActivityLine />
      <div className="mx-auto w-full max-w-[var(--measure)] px-[var(--gutter)] pt-7 pb-[var(--dock-clearance)]">
        <header className="mb-10 md:mb-14">
          <Wordmark />
        </header>
        <AnimatePresence mode="wait" initial={false}>
          <motion.main key={location.pathname} {...PAGE_TRANSITION}>
            {outlet}
          </motion.main>
        </AnimatePresence>
      </div>
      <Dock onOpenCommands={() => setPalette(true)} />
      <CommandPalette open={palette} onClose={() => setPalette(false)} />
    </MotionConfig>
  )
}
