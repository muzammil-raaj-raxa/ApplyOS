import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { MotionGlobalConfig } from 'motion/react'
import { afterEach, vi } from 'vitest'

// Tests should not wait for animations.
MotionGlobalConfig.skipAnimations = true

let reducedMotion = true
export const setReducedMotion = (value: boolean) => {
  reducedMotion = value
}

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: query.includes('prefers-reduced-motion') ? reducedMotion : false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }),
})

class NoopObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', NoopObserver)
vi.stubGlobal('IntersectionObserver', NoopObserver)

afterEach(() => {
  cleanup()
  window.localStorage.clear()
  reducedMotion = true
  vi.unstubAllGlobals()
  vi.stubGlobal('ResizeObserver', NoopObserver)
  vi.stubGlobal('IntersectionObserver', NoopObserver)
})
