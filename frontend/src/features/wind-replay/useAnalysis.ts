import { useQuery } from '@tanstack/react-query'
import { fetchAnalysis } from './api'

export function useAnalysis(decisionDate: string, cutoffHour: number, enabled = true) {
  return useQuery({
    queryKey: ['wind-replay', decisionDate, cutoffHour],
    queryFn: ({ signal }) => fetchAnalysis(decisionDate, cutoffHour, signal),
    enabled: enabled && /^2026-01-\d{2}$/.test(decisionDate),
    // No previous-query placeholder: old results must never appear under new filters.
  })
}
