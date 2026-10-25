/** Mirrors backend/app/schemas.py; the backend validates this response contract. */
export type ForecastPeriod = {
  startTime: string
  publishTime: string | null
  forecastMw: number | null
  actualMw: number | null
  errorMw: number | null
}

export type Analysis = {
  decisionDate: string
  deliveryDate: string
  decisionTime: string
  cutoffHourUtc: number
  source: string
  fetchedAt: string
  coverage: {
    forecastPeriods: number
    matchedPeriods: number
    expectedPeriods: 24
    forecastResolutionMinutes: 60
    actualHalfHours: number
  }
  metrics: Metrics
  periods: ForecastPeriod[]
  warnings: string[]
}

export type Metrics = { maeMw: number | null; biasMw: number | null; rmseMw: number | null }

export type DayMetrics = Metrics & { decisionDate: string; deliveryDate: string; matchedPeriods: number }

export type HourOfDayMetrics = Metrics & { hourUtc: number; matchedPeriods: number }

/** Mirrors SummaryResponse in backend/app/schemas.py. */
export type Summary = {
  cutoffHourUtc: number
  firstDecisionDate: string
  lastDecisionDate: string
  source: string
  fetchedAt: string
  coverage: { requestedDays: number; analysedDays: number; matchedHours: number; expectedHours: number }
  metrics: Metrics
  meanActualMw: number | null
  maePctOfMeanActual: number | null
  errorStdDevMw: number | null
  errorPercentilesMw: { p10: number | null; p50: number | null; p90: number | null }
  absErrorPercentilesMw: { p50: number | null; p90: number | null; p95: number | null }
  byHour: HourOfDayMetrics[]
  days: DayMetrics[]
  warnings: string[]
}
