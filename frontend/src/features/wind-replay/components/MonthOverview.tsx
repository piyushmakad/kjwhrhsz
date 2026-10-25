import type { Summary } from '../types'

import { fmt, shortDate, signed } from '../format'

import { Metric } from './MetricCards'

import { BarChart } from './BarChart'



type Props = { data: Summary; onSelectDay: (decisionDate: string) => void }



export function MonthOverview({ data, onSelectDay }: Props) {

  const { metrics, coverage, errorPercentilesMw: spread } = data

  const shortfall = spread.p90 != null && spread.p90 > 0 ? spread.p90 : null

  const surplus = spread.p10 != null && spread.p10 < 0 ? -spread.p10 : null

  // Flag when the average signed error explains most of the typical miss.

  const persistentBias = metrics.biasMw != null && metrics.maeMw != null && data.errorStdDevMw != null

    && Math.abs(metrics.biasMw) > 0.5 * metrics.maeMw



  return <>

    <section className="metrics">

      <Metric label="January MAE" value={`${fmt(metrics.maeMw, 0)} MW`}

        note={data.maePctOfMeanActual != null

          ? `${fmt(data.maePctOfMeanActual, 1)}% of mean wind output (${fmt((data.meanActualMw ?? 0) / 1000, 1)} GW)`

          : 'Average size of the miss'} />

      <Metric label="January bias" value={`${signed(metrics.biasMw)} MW`} note="Positive means wind was overestimated" />

      <Metric label="P90 shortfall" value={shortfall != null ? `${fmt(shortfall, 0)} MW` : '—'}

        note="Wind fell short by less than this in 90% of hours" />

      <Metric label="Hours scored" value={`${coverage.matchedHours} / ${coverage.expectedHours}`}

        note={`${coverage.analysedDays} of ${coverage.requestedDays} decision dates`} />

    </section>



    {shortfall != null && <section className="panel callout-panel">

      <div className="eyebrow">WHAT THIS MEANS FOR BUYING</div>

      <p className="lead">

        Treat the decision-time wind forecast as a central estimate, not a firm volume. Across January,

        wind came in more than <strong>{fmt(shortfall, 0)} MW</strong> below forecast in only 1 hour in 10

        {surplus != null && <> and more than <strong>{fmt(surplus, 0)} MW</strong> above it in 1 hour in 10</>}.

        Covering that shortfall band with other supply would have protected roughly 90% of hours against a wind miss.

      </p>

      {persistentBias && <p className="lead">

        Most of the miss is a <strong>persistent {signed(metrics.biasMw)} MW offset</strong>, not random error.

        Correcting for it would leave about <strong>±{fmt(data.errorStdDevMw, 0)} MW</strong> of hour-to-hour

        uncertainty (one standard deviation). Part of the offset may be a coverage difference: WINDFOR forecasts

        wind farms with operational metering, while FUELHH reports wind outturn by fuel type, so the two may not

        describe the same fleet. Confirm which forecast the desk actually trades on before applying a correction.

      </p>}

      <p className="subtle">Typical miss (median absolute error): {fmt(data.absErrorPercentilesMw.p50, 0)} MW ·

        P95 absolute error: {fmt(data.absErrorPercentilesMw.p95, 0)} MW · RMSE {fmt(metrics.rmseMw, 0)} MW.

        Retrospective statistics for one month; validate against more history before setting policy.</p>

    </section>}



    <section className="panel">

      <div className="panel-heading">

        <div><div className="eyebrow">ACCURACY BY DECISION DATE</div><h2>Daily mean absolute error</h2></div>

        <span className="subtle">Select a day to replay it</span>

      </div>

      <BarChart

        ariaLabel="Mean absolute error of the decision-time wind forecast for each January decision date"

        bars={data.days.map(day => ({

          key: day.decisionDate,

          label: String(Number(day.decisionDate.slice(8))),

          value: day.maeMw,

          tooltip: `Decision ${shortDate(day.decisionDate)} for ${shortDate(day.deliveryDate)} delivery: `

            + `MAE ${fmt(day.maeMw, 0)} MW, bias ${signed(day.biasMw)} MW, ${day.matchedPeriods}/24 hours`,

        }))}

        onSelect={onSelectDay}

      />

      <div className="panel-foot">Bars are labelled by January decision date; each covers the following delivery day.</div>

    </section>



    <section className="panel">

      <div className="panel-heading">

        <div><div className="eyebrow">ACCURACY BY DELIVERY HOUR</div><h2>Bias by hour of day</h2></div>

        <div className="legend">

          <span><i className="legend-swatch over" /> Wind overestimated</span>

          <span><i className="legend-swatch under" /> Wind underestimated</span>

        </div>

      </div>

      <BarChart

        signed

        ariaLabel="Average forecast bias for each delivery hour across January"

        bars={data.byHour.map(hour => ({

          key: String(hour.hourUtc),

          label: String(hour.hourUtc).padStart(2, '0'),

          value: hour.biasMw,

          tooltip: `${String(hour.hourUtc).padStart(2, '0')}:00 UK: bias ${signed(hour.biasMw)} MW, `

            + `MAE ${fmt(hour.maeMw, 0)} MW over ${hour.matchedPeriods} days`,

        }))}

      />

      <div className="panel-foot">Delivery hour in UK time (GMT). Later delivery hours are further ahead of the decision cutoff.</div>

    </section>

  </>

}

