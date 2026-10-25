import { useState } from 'react'
import type { ForecastPeriod } from '../types'
import { fmt, signed, stamp } from '../format'

export function TrendChart({ periods }: { periods: ForecastPeriod[] }) {
  const [active, setActive] = useState<number | null>(null)
  const width = 980, height = 320, left = 52, right = 20, top = 32, bottom = 38
  const values = periods.flatMap(p => [p.forecastMw, p.actualMw]).filter((v): v is number => v != null)
  if (!values.length) return <div className="chart-empty">No generation values are available for this delivery day.</div>

  const minimum = Math.min(0, ...values)
  const maximum = Math.max(1, ...values) * 1.1
  const start = Date.parse(periods[0].startTime)
  const duration = Math.max(Date.parse(periods[periods.length - 1].startTime) - start, 1)
  const x = (p: ForecastPeriod) => left + (Date.parse(p.startTime) - start) / duration * (width - left - right)
  const y = (value: number) => height - bottom - (value - minimum) / (maximum - minimum) * (height - top - bottom)
  // Each hour owns the band halfway to its neighbours, so hovering anywhere selects the nearest hour.
  const band = (width - left - right) / Math.max(periods.length - 1, 1)

  function path(key: 'forecastMw' | 'actualMw') {
    let previousMissing = true
    return periods.map(period => {
      const value = period[key]
      if (value == null) { previousMissing = true; return '' }
      const segment = `${previousMissing ? 'M' : 'L'} ${x(period).toFixed(1)} ${y(value).toFixed(1)}`
      previousMissing = false
      return segment
    }).join(' ')
  }

  const hovered = active != null ? periods[active] : null
  const hoveredX = hovered ? x(hovered) : 0
  const flip = hoveredX > width * 0.62

  return <div className="chart-scroll">
    <div className="chart-frame" onMouseLeave={() => setActive(null)}>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Hourly decision-time wind forecast and retrospective actual generation">
        {[0, .25, .5, .75, 1].map(fraction => {
          const value = minimum + (maximum - minimum) * fraction
          return <g key={fraction}>
            <line className="grid" x1={left} x2={width - right} y1={y(value)} y2={y(value)} />
            <text className="axis" x={left - 10} y={y(value) + 4} textAnchor="end">{fmt(value / 1000, 1)}</text>
          </g>
        })}
        <text className="axis-title" x="8" y="13">GW</text>
        {periods.filter((_, index) => index % 6 === 0).map(period => (
          <text key={period.startTime} className="axis" x={x(period)} y={height - 13} textAnchor="middle">
            {stamp(period.startTime).split(', ').pop()}
          </text>
        ))}
        {hovered && <line className="hover-guide" x1={hoveredX} x2={hoveredX} y1={top} y2={height - bottom} />}
        <path className="line forecast" d={path('forecastMw')} />
        <path className="line actual" d={path('actualMw')} />
        {periods.map((p, index) => <g key={p.startTime}>
          {p.forecastMw != null && <circle cx={x(p)} cy={y(p.forecastMw)} r={index === active ? 5.5 : 3} fill="#1e9a78" />}
          {index === active && p.actualMw != null && <circle cx={x(p)} cy={y(p.actualMw)} r="5.5" fill="#d2934e" />}
        </g>)}
        {periods.map((p, index) => (
          <rect
            key={p.startTime}
            className="hover-zone"
            x={x(p) - band / 2} y={top} width={band} height={height - top - bottom}
            onMouseEnter={() => setActive(index)}
            onClick={() => setActive(index)}
          />
        ))}
      </svg>
      {hovered && <div
        className={`chart-tooltip${flip ? ' flip' : ''}`}
        style={{ left: `${hoveredX / width * 100}%`, top: `${top / height * 100}%` }}
        role="status"
      >
        <div className="tooltip-time">{stamp(hovered.startTime)} UK</div>
        <div className="tooltip-row"><i className="legend-line forecast" />Forecast<b>{fmt(hovered.forecastMw)} MW</b></div>
        <div className="tooltip-row"><i className="legend-line actual" />Actual<b>{fmt(hovered.actualMw)} MW</b></div>
        <div className="tooltip-row">Error<b className={hovered.errorMw != null && hovered.errorMw > 0 ? 'positive' : 'negative'}>
          {signed(hovered.errorMw)} MW</b></div>
        <div className="tooltip-note">Forecast published {stamp(hovered.publishTime)}</div>
      </div>}
    </div>
  </div>
}
