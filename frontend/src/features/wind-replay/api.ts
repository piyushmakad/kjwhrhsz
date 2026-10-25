import { getJson } from '../../lib/api-client'
import type { Analysis, Summary } from './types'

export function fetchAnalysis(decisionDate: string, cutoffHour: number, signal?: AbortSignal) {
  const query = new URLSearchParams({
    decision_date: decisionDate,
    cutoff_hour: String(cutoffHour),
  })
  return getJson<Analysis>(`/api/analysis?${query}`, signal)
}

export function fetchSummary(cutoffHour: number, signal?: AbortSignal) {
  const query = new URLSearchParams({ cutoff_hour: String(cutoffHour) })
  return getJson<Summary>(`/api/summary?${query}`, signal)
}
