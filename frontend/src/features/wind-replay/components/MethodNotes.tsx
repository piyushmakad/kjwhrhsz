import type { Analysis } from '../types'
import { fmt, stamp } from '../format'

export function MethodNotes({ data }: { data: Analysis }) {
  const biggest = data.periods.filter(p => p.errorMw != null)
    .reduce<(typeof data.periods)[number] | undefined>((best, p) => !best || Math.abs(p.errorMw!) > Math.abs(best.errorMw!) ? p : best, undefined)

  return <section className="lower">
    <div className="panel insight">
      <div className="eyebrow">DECISION CONTEXT</div><h2>What was knowable?</h2>
      <p>The green curve uses the latest forecast for each target published by <strong>{stamp(data.decisionTime)} UTC</strong>.
        Actuals and error scores are retrospective: they became known after delivery.</p>
      {biggest && <div className="callout">
        <div className="callout-title">Largest observed miss</div>
        <strong>{fmt(Math.abs(biggest.errorMw!), 1)} MW</strong><span> at {stamp(biggest.startTime)}</span>
        <p>{biggest.errorMw! > 0 ? 'Actual wind was below the forecast.' : biggest.errorMw! < 0 ? 'Actual wind was above the forecast.' : 'Forecast and actual generation matched.'}</p>
      </div>}
    </div>
    <div className="panel method">
      <div className="eyebrow">METHOD & DATA QUALITY</div><h2>How this is calculated</h2>
      <ol>
        <li>Keep WINDFOR publications at or before the selected cutoff.</li>
        <li>Choose the newest eligible forecast for each delivery hour.</li>
        <li>Average both FUELHH <strong>WIND</strong> half-hours within that hour.</li>
        <li>Calculate error as forecast minus actual; score matched hours only.</li>
      </ol>
      <p className="fine">Alignment assumption: each hourly forecast is compared with the following hour's mean actual MW.
        Elexon covers Great Britain operational wind; demand and other supply are outside this pilot.</p>
      <p className="fine">The default 09:00 cutoff is the last whole hour before the GB day-ahead hourly auctions close (EPEX 09:20, N2EX 09:50 UK time). Bids must be in before then, so later forecasts could not inform them.</p>
    </div>
  </section>
}
