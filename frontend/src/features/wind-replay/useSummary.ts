import { useQuery } from '@tanstack/react-query'
import { fetchSummary } from './api'

export function useSummary(cutoffHour: number, enabled = true) {
  return useQuery({
    queryKey: ['wind-replay-summary', cutoffHour],
    queryFn: ({ signal }) => fetchSummary(cutoffHour, signal),
    enabled,
  })
}
