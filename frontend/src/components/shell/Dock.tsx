import { motion } from 'motion/react'
import { NavLink } from 'react-router-dom'
import { SPRING } from '../../lib/motion'
import { JobsIcon, SearchIcon, SourcesIcon, TodayIcon } from '../ui/icons'
import { StatusOrb } from './StatusPopover'

const MOD_KEY = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform) ? '⌘' : 'Ctrl'

const ITEMS = [
  { to: '/', label: 'Today', icon: TodayIcon, end: true },
  { to: '/jobs', label: 'Jobs', icon: JobsIcon, end: false },
  { to: '/sources', label: 'Sources', icon: SourcesIcon, end: false },
]

/**
 * Navigation lives in a floating dock instead of a sidebar, the way an operating system keeps
 * its apps. Future versions add their own items here. The highlight glides to the active one.
 */
export function Dock({ onOpenCommands }: { onOpenCommands: () => void }) {
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-[max(1rem,env(safe-area-inset-bottom))] z-40 flex justify-center px-3"
    >
      <div className="glass flex w-full max-w-md items-center gap-1 rounded-full p-1.5 md:w-auto md:max-w-none">
        {ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `relative flex h-11 flex-1 items-center justify-center gap-2.5 rounded-full px-4 text-label transition-colors duration-150 md:flex-none md:px-5 ${isActive ? 'text-pearl' : 'text-mist hover:text-pearl'}`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.span
                    layoutId="dock-active"
                    transition={SPRING}
                    className="absolute inset-0 rounded-full bg-white/[0.13] shadow-[inset_0_1px_0_rgb(255_255_255/0.14),0_0_24px_-6px_rgb(124_242_184/0.4)]"
                    aria-hidden="true"
                  />
                )}
                <Icon className="relative" />
                <span className="relative text-[0.8125rem] font-semibold">{label}</span>
              </>
            )}
          </NavLink>
        ))}
        <span className="mx-1 hidden h-6 w-px bg-white/10 md:block" aria-hidden="true" />
        <button
          type="button"
          onClick={onOpenCommands}
          aria-label="Open commands"
          className="grid h-11 w-11 place-items-center rounded-full text-mist transition hover:bg-white/[0.08] hover:text-pearl md:w-auto md:grid-flow-col md:gap-2 md:px-4"
        >
          <SearchIcon />
          <kbd className="hidden rounded-md bg-white/10 px-1.5 py-0.5 text-[0.6875rem] font-semibold text-mist md:block">{MOD_KEY} K</kbd>
        </button>
        <StatusOrb />
      </div>
    </nav>
  )
}
