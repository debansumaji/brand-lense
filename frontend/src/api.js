const browserHost = typeof window !== 'undefined' ? window.location.hostname : ''
const localHost = browserHost === 'localhost' || !browserHost ? '127.0.0.1' : browserHost
const API_URL = import.meta.env.VITE_API_URL || `http://${localHost}:8000`
const DEMO_BASE_URL = `http://${localHost}:8000/demo`

export const DEMO_LINKS = [
  { label: 'Demo match', url: `${DEMO_BASE_URL}/demo_match.html` },
  { label: 'Demo no ANC', url: `${DEMO_BASE_URL}/demo_noanc.html` },
  { label: 'Demo missing info', url: `${DEMO_BASE_URL}/demo_missing.html` },
]

export async function analyzeProduct(payload) {
  try {
    const response = await fetch(`${API_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    let data = null
    try {
      data = await response.json()
    } catch {
      // The status below still gives the user a useful error if the server
      // returns a non-JSON response.
    }

    if (!response.ok) {
      const detail = data?.detail
      const error = new Error(
        detail?.message || (typeof detail === 'string' ? detail : `Request failed (${response.status}).`),
      )
      error.code = detail?.code || `HTTP_${response.status}`
      error.isApiError = true
      throw error
    }

    return data
  } catch (error) {
    if (error?.isApiError) throw error

    const networkError = new Error("Can't reach the server. Is the backend running?")
    networkError.code = 'NETWORK_ERROR'
    throw networkError
  }
}
