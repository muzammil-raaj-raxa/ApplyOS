import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './api'

export function makeQueryClient({ retry = true }: { retry?: boolean } = {}): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 15_000,
        refetchOnWindowFocus: false,
        // A 4xx will not fix itself on retry.
        retry: retry ? (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 1 : false,
      },
    },
  })
}
