import { motion } from 'motion/react'
import { useId } from 'react'
import { usePrefersReducedMotion } from '../../hooks/useMedia'
import { bandFor, DIMENSIONS } from '../../lib/format'
import { EASE_OUT } from '../../lib/motion'
import type { ScoreSummary } from '../../lib/types'
import { AnimatedNumber } from './AnimatedNumber'

type Parts = Pick<ScoreSummary, 'technical' | 'experience' | 'seniority' | 'location' | 'authorization' | 'role' | 'domain'>

interface FitRingProps {
  score: number | null
  /** Per-dimension scores. Each arc is as long as its weight and as full as its score. */
  parts?: Parts | null
  size?: number
  /** Draw the arcs in and count the number up. Use when a score is shown because of an action. */
  animate?: boolean
  /** A score is being worked out right now. */
  working?: boolean
  showBand?: boolean
}


function arcPath(cx: number, r: number, startDeg: number, endDeg: number): string {
  const point = (deg: number) => {
    const rad = ((deg - 90) * Math.PI) / 180
    return `${(cx + r * Math.cos(rad)).toFixed(3)} ${(cx + r * Math.sin(rad)).toFixed(3)}`
  }
  return `M${point(startDeg)} A${r} ${r} 0 ${endDeg - startDeg > 180 ? 1 : 0} 1 ${point(endDeg)}`
}

/**
 * The product's signature mark. The ring is split into seven arcs, one per scoring dimension.
 * An arc's length is its weight in the overall score; how full it is shows how well the job
 * scores there. So one glance shows the grade, and the shape shows where it came from.
 */
export function FitRing({ score, parts, size = 56, animate = false, working = false, showBand = false }: FitRingProps) {
  const gradientId = useId()
  const reduced = usePrefersReducedMotion()
  const draw = animate && !reduced

  const stroke = Math.max(3, Math.round(size * 0.075))
  const cx = size / 2
  const r = cx - stroke / 2 - 1
  const gapDeg = ((stroke * 1.7) / r) * (180 / Math.PI)
  const room = 360 - DIMENSIONS.length * gapDeg

  if (score === null) {
    return (
      <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={working ? 'Scoring this job' : 'Not scored yet'}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className={working ? 'animate-orbit' : ''}>
          <circle cx={cx} cy={cx} r={r} fill="none" stroke="rgb(255 255 255 / 0.2)" strokeWidth={stroke * 0.5} strokeDasharray={`${stroke * 0.4} ${stroke * 1.9}`} strokeLinecap="round" />
        </svg>
        {!working && (
          <span className="absolute inset-0 grid place-items-center text-mist/70" style={{ fontSize: size * 0.3 }}>
            –
          </span>
        )}
      </div>
    )
  }

  const band = bandFor(score)
  const arcs = DIMENSIONS.map((dim, index) => {
    const before = DIMENSIONS.slice(0, index).reduce((sum, d) => sum + (room * d.weight) / 100 + gapDeg, gapDeg / 2)
    const span = (room * dim.weight) / 100
    const value = parts ? parts[dim.key] : score
    return { key: dim.key, d: arcPath(cx, r, before, before + span), fraction: Math.max(0, Math.min(1, value / 100)), index }
  })

  return (
    <div
      className="relative shrink-0"
      style={{
        width: size,
        height: size,
        filter: band.glow ? `drop-shadow(0 0 ${size * 0.1}px color-mix(in srgb, ${band.color} 38%, transparent))` : undefined,
        transition: 'filter 300ms var(--ease-out-expo)',
      }}
      role="img"
      aria-label={`Fit score ${score} out of 100. ${band.label}.`}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} overflow="visible">
        <defs>
          <linearGradient id={gradientId} gradientUnits="userSpaceOnUse" x1="0" y1="0" x2={size} y2={size}>
            <stop offset="0" style={{ stopColor: `color-mix(in srgb, ${band.color} 62%, white)` }} />
            <stop offset="1" style={{ stopColor: band.color }} />
          </linearGradient>
        </defs>
        {arcs.map((arc) => (
          <path key={`t-${arc.key}`} d={arc.d} fill="none" stroke="rgb(255 255 255 / 0.1)" strokeWidth={stroke} strokeLinecap="round" />
        ))}
        {arcs.map((arc) =>
          arc.fraction > 0 ? (
            <motion.path
              key={`f-${arc.key}`}
              d={arc.d}
              fill="none"
              stroke={`url(#${gradientId})`}
              strokeWidth={stroke}
              strokeLinecap="round"
              initial={draw ? { pathLength: 0 } : false}
              animate={{ pathLength: arc.fraction }}
              transition={{ duration: draw ? 0.95 : 0.4, ease: EASE_OUT, delay: draw ? arc.index * 0.07 : 0 }}
            />
          ) : null,
        )}
      </svg>
      <div className="absolute inset-0 grid place-content-center text-center leading-none">
        <span className="font-[650] tracking-tight text-pearl" style={{ fontSize: size * 0.34 }}>
          {draw ? <AnimatedNumber value={score} /> : <span className="tnum">{score}</span>}
        </span>
        {showBand && size >= 140 && (
          <span className="mt-2 text-label" style={{ color: band.color }}>
            {band.label}
          </span>
        )}
      </div>
    </div>
  )
}

