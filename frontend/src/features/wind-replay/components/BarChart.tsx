import { fmt } from '../format'

export type Bar = { key: string; label: string; value: number | null; tooltip: string }

type Props = {
  bars: Bar[]
  ariaLabel: string
  /** Signed values colour by direction; unsigned values use one colour. */
  signed?: boolean
  selectedKey?: string
  onSelect?: (key: string) => void
}

export function BarChart({ bars, ariaLabel, signed = false, selectedKey, onSelect }: Props) {
  const width = 980, height = 230, left = 52, right = 12, top = 30, bottom = 30
  const values = bars.map(bar => bar.value).filter((v): v is number => v != null)
  if (!values.length) return <div className="chart-empty">No matched hours are available.</div>

  const minimum = Math.min(0, ...values) * 1.1
  const maximum = Math.max(1, ...values) * 1.1
  const slot = (width - left - right) / bars.length
  const y = (value: number) => top + (maximum - value) / (maximum - minimum) * (height - top - bottom)
  const ticks = [minimum, minimum < 0 ? 0 : (maximum + minimum) / 2, maximum]

  return <div className="chart-scroll">
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
      {ticks.map(value => <g key={value}>
        <line className={value === 0 ? 'zero' : 'grid'} x1={left} x2={width - right} y1={y(value)} y2={y(value)} />
        <text className="axis" x={left - 8} y={y(value) + 4} textAnchor="end">{fmt(value)}</text>
      </g>)}
      <text className="axis-title" x="8" y="12">MW</text>
      {bars.map((bar, index) => {
        const x = left + index * slot
        const tone = bar.value == null ? '' : !signed ? 'neutral' : bar.value > 0 ? 'over' : 'under'
        const interactive = Boolean(onSelect)
        return <g
          key={bar.key}
          className={`bar ${tone}${bar.key === selectedKey ? ' selected' : ''}${interactive ? ' interactive' : ''}`}
          role={interactive ? 'button' : undefined}
          tabIndex={interactive ? 0 : undefined}
          aria-label={interactive ? bar.tooltip : undefined}
          onClick={interactive ? () => onSelect?.(bar.key) : undefined}
          onKeyDown={interactive ? event => {
            if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect?.(bar.key) }
          } : undefined}
        >
          <title>{bar.tooltip}</title>
          <rect className="hit" x={x} y={top} width={slot} height={height - top - bottom} />
          {bar.value != null && <rect
            x={x + slot * 0.18} width={slot * 0.64}
            y={Math.min(y(bar.value), y(0))} height={Math.max(Math.abs(y(bar.value) - y(0)), 1)} rx="2"
          />}
          <text className="axis" x={x + slot / 2} y={height - 10} textAnchor="middle">{bar.label}</text>
        </g>
      })}
    </svg>
  </div>
}
