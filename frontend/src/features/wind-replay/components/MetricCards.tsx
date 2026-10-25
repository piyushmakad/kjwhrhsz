import type { Analysis } from '../types'
import { fmt } from '../format'

export function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="metric">
    <div className="metric-label">{label}</div>
    <div className="metric-value">{value}</div>
    <div className="metric-note">{note}</div>
  </div>
}

export function MetricCards({ data }: { data: Analysis }) {
  const bias = data.metrics.biasMw
  return <section className="metrics">
    <Metric label="Mean absolute error" value={`${fmt(data.metrics.maeMw, 1)} MW`} note="Average size of the miss" />
    <Metric label="Forecast bias" value={`${bias != null && bias > 0 ? '+' : ''}${fmt(bias, 1)} MW`} note="Positive means wind was overestimated" />
    <Metric label="RMSE" value={`${fmt(data.metrics.rmseMw, 1)} MW`} note="Highlights large misses" />
    <Metric label="Matched periods" value={`${data.coverage.matchedPeriods} / ${data.coverage.expectedPeriods}`} note="Hourly forecasts paired with actual wind" />
  </section>
}
