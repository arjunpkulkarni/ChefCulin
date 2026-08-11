/**
 * Thin client for the CulinAI FastAPI backend.
 * Vite proxies /api → http://127.0.0.1:8000 (see vite.config.js).
 */

const BASE = import.meta.env.VITE_API_BASE || '/api'

async function get(path, params = {}) {
  const url = new URL(BASE + path, window.location.origin)
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

export async function health() {
  return get('/health')
}

export async function cooccur(ingredient, n = 20) {
  return get('/cooccur', { ingredient, n })
}

export async function techniques(ingredient, n = 10) {
  return get('/techniques', { ingredient, n })
}

export async function listPalate(userId, limit = 50) {
  return get('/palate', { user_id: userId, limit })
}

export async function savePalate(body) {
  const res = await fetch(new URL(BASE + '/palate', window.location.origin), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`save failed: ${res.status}`)
  return res.json()
}
