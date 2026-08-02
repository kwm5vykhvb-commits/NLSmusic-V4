const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function parseResponse(response) {
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || 'Request failed')
  }
  return response.json()
}

export async function searchTracks(query, tab, page) {
  const params = new URLSearchParams({ query, tab, page: String(page) })
  const response = await fetch(`${API_BASE}/api/search?${params}`)
  return parseResponse(response)
}

export async function fetchSuggestions(query) {
  const response = await fetch(`${API_BASE}/api/suggestions?query=${encodeURIComponent(query)}`)
  return parseResponse(response)
}

export function downloadTrack(trackId) {
  window.open(`${API_BASE}/api/download/${encodeURIComponent(trackId)}`, '_blank', 'noopener,noreferrer')
}

export function streamTrackUrl(trackId) {
  return `${API_BASE}/api/stream/${encodeURIComponent(trackId)}`
}

export async function fetchDownloads() {
  const response = await fetch(`${API_BASE}/api/downloads`)
  return parseResponse(response)
}
