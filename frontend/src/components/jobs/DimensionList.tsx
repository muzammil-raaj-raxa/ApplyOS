import { motion } from 'motion/react'
import { bandFor, DIMENSIONS } from '../../lib/format'
import { EASE_OUT } from '../../lib/motion'
import type { ScoreSummary } from '../../lib/types'

/** The seven parts of the score, with how much each counts and who judged it. */
export function DimensionList({ score }: { score: ScoreSummary }) {
  return (
    <ul className="space-y-4">
      {DIMENSIONS.map((dim, index) => {
        const value = score[dim.key]
        return (
          <li key={dim.key} className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-4 gap-y-2" title={dim.hint}>
            <div className="flex min-w-0 items-baseline gap-2.5">
              <span className="truncate text-pearl">{dim.label}</span>
              <span className="shrink-0 text-label font-normal text-fog">counts {dim.weight}%</span>
              <span className="shrink-0 rounded-full bg-white/[0.07] px-2 py-px text-[0.6875rem] font-semibold text-mist">{dim.by === 'AI' ? 'AI judged' : 'Calculated'}</span>
            </div>
            <span className="tnum text-right font-semibold text-pearl">{value}</span>
            <div className="col-span-2 h-1.5 overflow-hidden rounded-full bg-white/[0.09]">
              <motion.div
                className="h-full rounded-full"
                style={{ background: bandFor(value).color }}
                initial={{ width: 0 }}
                animate={{ width: `${value}%` }}
                transition={{ duration: 0.8, ease: EASE_OUT, delay: 0.1 + index * 0.05 }}
              />
            </div>
          </li>
        )
      })}
    </ul>
  )
}
