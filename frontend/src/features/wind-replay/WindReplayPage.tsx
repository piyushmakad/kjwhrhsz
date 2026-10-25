import { useState } from 'react'
import { useAnalysis } from './useAnalysis'
import { useSummary } from './useSummary'
import { dateLabel, stamp } from './format'
import { TrendChart } from './components/TrendChart'
import { MetricCards } from './components/MetricCards'
import { ForecastTable } from './components/ForecastTable'
import { MethodNotes } from './components/MethodNotes'
import { MonthOverview } from './components/MonthOverview'

type View = 'month' | 'day'

// January is GMT, so these UTC hours are also UK local time.
const DEFAULT_CUTOFF_HOUR = 9
const CUTOFF_NOTES: Record<number, string> = {
  9: 'before EPEX 09:20 and N2EX 09:50 hourly auctions',
  15: 'before EPEX 15:30 half-hourly auction',
}

export function WindReplayPage() {
  const [view, setView] = useState<View>('month')
  const [decisionDate, setDecisionDate] = useState('2026-01-12')
  const [cutoffHour, setCutoffHour] = useState(DEFAULT_CUTOFF_HOUR)
  const validSelection = /^2026-01-\d{2}$/.test(decisionDate)
  const summary = useSummary(cutoffHour, view === 'month')
  const day = useAnalysis(decisionDate, cutoffHour, view === 'day')
  const delivery = validSelection ? new Date(`${decisionDate}T00:00:00Z`) : null
  if (delivery) delivery.setUTCDate(delivery.getUTCDate() + 1)

  function openDay(date: string) {
    setDecisionDate(date)
    setView('day')
  }

  return <>
    <section className="hero">
      <div className="eyebrow">DAY-AHEAD PROCUREMENT · JANUARY 2026 PILOT</div>
      <h1>Wind decision replay</h1>
      <p>See the forecast available when a buying decision was made, then measure how far wind missed it.</p>
    </section>
    <div className="tabs" role="tablist" aria-label="Analysis view">
      <button role="tab" aria-selected={view === 'month'} className={view === 'month' ? 'active' : ''} onClick={() => setView('month')}>January overview</button>
      <button role="tab" aria-selected={view === 'day'} className={view === 'day' ? 'active' : ''} onClick={() => setView('day')}>Day replay</button>
    </div>
    <section className="controls">
      {view === 'day' && <div className="control">
        <label htmlFor="date">Decision date</label>
        <input id="date" type="date" min="2026-01-01" max="2026-01-31" value={decisionDate} onChange={e => setDecisionDate(e.target.value)} />
      </div>}
      <div className="control">
        <label htmlFor="cutoff">Decision cutoff (UK = UTC in January)</label>
        <select id="cutoff" value={cutoffHour} onChange={e => setCutoffHour(Number(e.target.value))}>
          {Array.from({ length: 24 }, (_, hour) => <option key={hour} value={hour}>
            {String(hour).padStart(2, '0')}:00{CUTOFF_NOTES[hour] ? ` — ${CUTOFF_NOTES[hour]}` : ''}
          </option>)}
        </select>
      </div>
      <div className="control-info">
        {view === 'day'
          ? <strong>Delivery: {delivery && Number.isFinite(delivery.getTime()) ? dateLabel(delivery.toISOString().slice(0, 10)) : 'select a decision date'}</strong>
          : <strong>All 31 January decision dates · delivery 2 Jan – 1 Feb</strong>}
        <span>Latest forecast published by the cutoff, per delivery hour</span>
      </div>
    </section>

    {view === 'month' && <>
      {summary.isPending && <div className="notice" role="status">Loading every January decision date from Elexon… the first load can take several seconds.</div>}
      {summary.error && <div className="notice error" role="alert">
        <strong>Could not load the January overview.</strong> {summary.error.message}
        <button onClick={() => void summary.refetch()}>Retry</button>
      </div>}
      {summary.data && <>
        {summary.data.warnings.length > 0 && <div className="notice" role="status">{summary.data.warnings.join(' ')}</div>}
        <MonthOverview data={summary.data} onSelectDay={openDay} />
        <footer>{summary.data.source} · Retrieved {stamp(summary.data.fetchedAt)} UTC{summary.isFetching ? ' · Refreshing…' : ''}</footer>
      </>}
    </>}

    {view === 'day' && <>
      {!validSelection && <div className="notice">Select a decision date in January 2026.</div>}
      {validSelection && day.isPending && <div className="notice" role="status">Loading Elexon forecasts and actuals for this selection…</div>}
      {day.error && <div className="notice error" role="alert">
        <strong>Could not load this analysis.</strong> {day.error.message}
        <button onClick={() => void day.refetch()}>Retry</button>
      </div>}
      {day.data && <>
        {day.data.warnings.length > 0 && <div className="notice" role="status">{day.data.warnings.join(' ')}</div>}
        <MetricCards data={day.data} />
        <section className="panel chart-panel">
          <div className="panel-heading">
            <div><div className="eyebrow">DELIVERY DAY · {dateLabel(day.data.deliveryDate).toUpperCase()}</div><h2>Forecast vs actual wind</h2></div>
            <div className="legend">
              <span><i className="legend-line forecast" /> Decision-time forecast</span>
              <span><i className="legend-line actual" /> Retrospective actual</span>
            </div>
          </div>
          <TrendChart periods={day.data.periods} />
          <div className="panel-foot">Values in MW; axis in GW. Actual half-hours are averaged within each forecast hour. UK times (GMT). Gaps remain visible.</div>
        </section>
        <MethodNotes data={day.data} />
        <ForecastTable data={day.data} />
        <footer>{day.data.source} · Retrieved {stamp(day.data.fetchedAt)} UTC{day.isFetching ? ' · Refreshing…' : ''}</footer>
      </>}
    </>}
  </>
}
