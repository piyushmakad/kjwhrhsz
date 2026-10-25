import type { Analysis } from '../types'
import { fmt, stamp } from '../format'

export function ForecastTable({ data }: { data: Analysis }) {
  return <section className="panel table-panel">
    <div className="panel-heading">
      <div><div className="eyebrow">AUDIT TRAIL</div><h2>Forecast-period detail</h2></div>
      <span className="subtle">{data.coverage.forecastPeriods} / 24 forecasts available</span>
    </div>
    <div className="table-scroll"><table>
      <thead><tr>
        <th>Delivery time (UK)</th><th>Forecast published (UK)</th>
        <th>Forecast MW</th><th>Actual MW</th><th>Error MW</th>
      </tr></thead>
      <tbody>{data.periods.map(period => <tr key={period.startTime}>
        <td>{stamp(period.startTime)}</td><td>{stamp(period.publishTime)}</td>
        <td>{fmt(period.forecastMw)}</td><td>{fmt(period.actualMw, 1)}</td>
        <td className={period.errorMw != null && period.errorMw > 0 ? 'positive' : 'negative'}>
          {period.errorMw != null && period.errorMw > 0 ? '+' : ''}{fmt(period.errorMw, 1)}
        </td>
      </tr>)}</tbody>
    </table></div>
  </section>
}
