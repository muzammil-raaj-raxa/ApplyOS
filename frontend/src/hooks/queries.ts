import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, PAGE_SIZE } from '../lib/api'
import type { JobFilters, SearchProfile } from '../lib/types'

export const keys = {
  stats: ['stats'] as const,
  jobs: (filters: JobFilters) => ['jobs', filters] as const,
  job: (id: number) => ['job', id] as const,
  searchProfile: ['search-profile'] as const,
  health: ['health'] as const,
  ai: ['ai-status'] as const,
}

export const useStats = () => useQuery({ queryKey: keys.stats, queryFn: api.stats })

export function useJobs(filters: JobFilters) {
  return useInfiniteQuery({
    queryKey: keys.jobs(filters),
    queryFn: ({ pageParam }) => api.jobs(filters, pageParam),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((sum, page) => sum + page.items.length, 0)
      return loaded < last.total && last.items.length === PAGE_SIZE ? loaded : undefined
    },
    placeholderData: (previous) => previous,
  })
}

export const useJob = (id: number | null) =>
  useQuery({ queryKey: keys.job(id ?? 0), queryFn: () => api.job(id as number), enabled: id !== null })

export const useSearchProfile = () => useQuery({ queryKey: keys.searchProfile, queryFn: api.searchProfile })

export const useHealth = () => useQuery({ queryKey: keys.health, queryFn: api.health, refetchInterval: 30_000 })

export const useAiStatus = () => useQuery({ queryKey: keys.ai, queryFn: api.aiStatus, refetchInterval: 30_000 })

/** Anything that changes jobs or scores refreshes the lists, the open job and the numbers. */
function useRefreshAll() {
  const client = useQueryClient()
  return () => Promise.all([
    client.invalidateQueries({ queryKey: ['jobs'] }),
    client.invalidateQueries({ queryKey: ['job'] }),
    client.invalidateQueries({ queryKey: keys.stats }),
    client.invalidateQueries({ queryKey: keys.ai }),
  ])
}

export function useDecision() {
  const refresh = useRefreshAll()
  return useMutation({
    mutationFn: ({ id, decision }: { id: number; decision: 'save' | 'reject' | 'clear' }) =>
      decision === 'save' ? api.save(id) : decision === 'reject' ? api.reject(id) : api.clearDecision(id),
    onSuccess: refresh,
  })
}

export function useScoreJob() {
  const refresh = useRefreshAll()
  return useMutation({
    mutationFn: ({ id, force = false }: { id: number; force?: boolean }) => api.scoreJob(id, force),
    onSettled: refresh,
  })
}

export function useScoreJobs() {
  const refresh = useRefreshAll()
  return useMutation({ mutationFn: (limit: number) => api.scoreJobs(limit), onSettled: refresh })
}

export function useFindJobs() {
  const refresh = useRefreshAll()
  return useMutation({ mutationFn: api.findJobs, onSettled: refresh })
}

export function useSaveSearchProfile() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (profile: SearchProfile) => api.saveSearchProfile(profile),
    onSuccess: (saved) => client.setQueryData(keys.searchProfile, saved),
  })
}
