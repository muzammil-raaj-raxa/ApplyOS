import { motion } from 'motion/react'
import { usePrefersReducedMotion } from '../../hooks/useMedia'
import { EASE_OUT } from '../../lib/motion'
import { AnimatedNumber } from './AnimatedNumber'

export interface Stage {
  key: string
  label: string
  count: number
  color: string
  /** Share of the previous stage that made it here, 0 to 1. */
  fraction: number
}

/**
 * The pipeline as concentric rings. The outer ring is everything found; each ring inside it
 * shows what share of the previous stage survived. This is the one orchestrated moment on
 * the Today page: the rings draw in from the outside, once.
 */
export function StageRings({ stages, size = 380, center }: { stages: Stage[]; size?: number; center: { value: number; label: string } }) {
  const reduced = usePrefersReducedMotion()
  const stroke = Math.round(size * 0.034)
  const gap = Math.round(size * 0.03)
  const cx = size / 2
  const outer = cx - stroke / 2 - 2

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={`Pipeline: ${stages.map((s) => `${s.count} ${s.label}`).join(', ')}.`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} overflow="visible">
        <g transform={`rotate(-90 ${cx} ${cx})`}>
          {stages.map((stage, i) => {
            const r = outer - i * (stroke + gap)
            const glow = i === stages.length - 1 && stage.fraction > 0
            return (
              <g key={stage.key} style={{ filter: glow ? `drop-shadow(0 0 ${size * 0.025}px color-mix(in srgb, ${stage.color} 55%, transparent))` : undefined }}>
                <circle cx={cx} cy={cx} r={r} fill="none" stroke="rgb(255 255 255 / 0.07)" strokeWidth={stroke} />
                {stage.fraction > 0 && (
                  <motion.circle
                    cx={cx}
                    cy={cx}
                    r={r}
                    fill="none"
                    stroke={stage.color}
                    strokeWidth={stroke}
                    strokeLinecap="round"
                    initial={reduced ? false : { pathLength: 0 }}
                    animate={{ pathLength: Math.min(1, stage.fraction) }}
                    transition={{ duration: 1.25, ease: EASE_OUT, delay: 0.15 + i * 0.14 }}
                  />
                )}
              </g>
            )
          })}
        </g>
      </svg>
      <div className="absolute inset-0 grid place-content-center text-center">
        <span className="font-[650] leading-none tracking-tight text-pearl" style={{ fontSize: size * 0.2 }}>
          <AnimatedNumber value={center.value} durationMs={1400} />
        </span>
        <span className="mt-2 text-label text-mist">{center.label}</span>
      </div>
    </div>
  )
}
