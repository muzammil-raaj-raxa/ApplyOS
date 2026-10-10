import { ApiError } from './api'

export function describeError(error: unknown): { title: string; body: string } {
  if (error instanceof ApiError) {
    if (error.status === 0) return { title: "Can't reach the backend", body: error.detail }
    if (error.status === 503) return { title: 'No AI is available right now', body: error.detail }
    return { title: 'That did not work', body: error.detail }
  }
  return { title: 'That did not work', body: error instanceof Error ? error.message : 'Unknown error.' }
}
