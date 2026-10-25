export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message)
  }
}

export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const base = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
  const response = await fetch(`${base}${path}`, { signal })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const message = typeof body.detail === 'string'
      ? body.detail
      : 'The request could not be completed. Check the selected date and retry.'
    throw new ApiError(message, response.status)
  }
  return response.json() as Promise<T>
}
