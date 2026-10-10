// The motion language. Motion answers an action or shows what changed; it is never decoration.

export const EASE_OUT = [0.16, 1, 0.3, 1] as const
export const EASE_IN_OUT = [0.76, 0, 0.24, 1] as const

export const DURATION = { quick: 0.14, base: 0.24, slow: 0.52, sweep: 0.95 } as const

/** Things that slide in because you asked for them (dossier, menus) use this spring. */
export const SPRING = { type: 'spring', stiffness: 420, damping: 40, mass: 0.9 } as const

/** Pages cross-fade with a small lift. Nothing else enters on its own. */
export const PAGE_TRANSITION = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE_OUT } },
  exit: { opacity: 0, transition: { duration: DURATION.quick } },
}
