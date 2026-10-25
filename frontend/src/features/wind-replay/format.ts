export const fmt = (value: number | null, digits = 0) => value == null
  ? '—'
  : new Intl.NumberFormat('en-GB', { maximumFractionDigits: digits }).format(value)

export const stamp = (value: string | null) => value == null ? '—' : new Date(value).toLocaleString('en-GB', {
  timeZone: 'Europe/London', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false,
})

export const dateLabel = (value: string) => new Date(`${value}T12:00:00Z`).toLocaleDateString('en-GB', {
  timeZone: 'Europe/London', weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
})

export const signed = (value: number | null, digits = 0) => `${value != null && value > 0 ? '+' : ''}${fmt(value, digits)}`

export const shortDate = (value: string) => new Date(`${value}T12:00:00Z`).toLocaleDateString('en-GB', {
  timeZone: 'Europe/London', day: 'numeric', month: 'short',
})
