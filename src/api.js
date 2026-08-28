/**
 * Thin client for the CulinAI FastAPI backend.
 * Vite proxies /api → http://127.0.0.1:8001 (see vite.config.js).
 */

const BASE = import.meta.env.VITE_API_BASE || '/api'

function requestUrl(path) {
  const p = path.startsWith('/') ? path : `/${path}`
  if (BASE.startsWith('http')) {
    const root = BASE.replace(/\/$/, '')
    return new URL(p, `${root}/`)
  }
  if (typeof window !== 'undefined' && window.location?.origin) {
    return new URL(BASE + p, window.location.origin)
  }
  const api =
    (typeof process !== 'undefined' && process.env?.CULIN_API) || 'http://127.0.0.1:8001'
  return new URL(p, `${api.replace(/\/$/, '')}/`)
}

async function get(path, params = {}) {
  const url = requestUrl(path)
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) url.searchParams.set(k, String(v))
  })
  const res = await fetch(url)
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}${detail ? `: ${detail}` : ''}`)
  }
  return res.json()
}

async function post(path, body) {
  const res = await fetch(requestUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}${detail ? `: ${detail}` : ''}`)
  }
  return res.json()
}

export async function health() {
  return get('/health')
}

export async function cooccur(ingredient, n = 20) {
  return get('/cooccur', { ingredient, n })
}

/** Flavor-network shared-compound neighbors (Ahn / FooDB projection). */
export async function compound(ingredient, n = 24) {
  return get('/compound', { ingredient, n })
}

export async function techniques(ingredient, n = 10) {
  return get('/techniques', { ingredient, n })
}

export async function listPalate(userId, limit = 50) {
  return get('/palate', { user_id: userId, limit })
}

export async function savePalate(body) {
  return post('/palate', body)
}
