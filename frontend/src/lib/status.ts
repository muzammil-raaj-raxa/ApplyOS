import type { AiStatus, Health } from './types'

export type Level = 'good' | 'warn' | 'bad'

export function systemLevel(health: Health | undefined, failed: boolean): Level {
  if (failed || !health || !health.backend || !health.database) return 'bad'
  if (!health.groq && !health.ollama) return 'bad'
  if (!health.groq || !health.ollama) return 'warn'
  return 'good'
}

export const LEVEL_COLOR: Record<Level, string> = { good: 'var(--color-mint)', warn: 'var(--color-apricot)', bad: 'var(--color-coral)' }

export function statusLines(health: Health | undefined, ai: AiStatus | undefined, failed: boolean) {
  if (failed || !health) {
    return [{ label: 'Backend', ok: false, note: "Can't reach it. Start ApplyOS with ./scripts/start.sh." }]
  }
  const resting = ai?.providers.filter((p) => p.cooldown_seconds > 0) ?? []
  return [
    { label: 'Backend', ok: health.backend, note: 'Running.' },
    { label: 'Database', ok: health.database, note: health.database ? 'Connected.' : 'Not answering. Check the data folder.' },
    {
      label: 'Groq',
      ok: health.groq,
      note: health.groq
        ? resting.some((p) => p.name === 'groq')
          ? `Resting for ${resting.find((p) => p.name === 'groq')?.cooldown_seconds}s after a rate limit.`
          : 'Key found. Cloud scoring is available.'
        : 'No key. Add GROQ_API_KEY to your .env file.',
    },
    {
      label: 'Ollama',
      ok: health.ollama,
      note: health.ollama ? 'Ready as the local fallback.' : 'Not running, or the model in OLLAMA_MODEL is not installed.',
    },
  ]
}
