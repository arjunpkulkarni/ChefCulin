/**
 * Session frame metadata — static FRAMES plus LLM-registered forms.
 */
import { FRAMES, OVERLAYS } from '../data/domain.js'

const EXTRA = new Map()

const OVERLAY_KEYS = new Set([
  'sear',
  'roast',
  'confit',
  'cure',
  'broth',
  'braise',
  'ground',
  'smoke',
  'terrine',
  'raw',
])

function normalizeFrame(meta = {}) {
  const overlay = OVERLAY_KEYS.has(meta.overlay) ? meta.overlay : 'raw'
  return {
    produces: Array.isArray(meta.produces) ? meta.produces : ['tender'],
    absent: Array.isArray(meta.absent) ? meta.absent : [],
    overlay,
    fat: typeof meta.fat === 'number' ? meta.fat : 0.45,
    overlayNote: typeof meta.overlayNote === 'string' ? meta.overlayNote : null,
  }
}

export function registerFrame(name, meta) {
  const key = String(name || '').trim()
  if (!key || !meta) return
  EXTRA.set(key, normalizeFrame(meta))
}

export function getFrame(name) {
  const key = String(name || '').trim()
  if (!key) return null
  return FRAMES[key] || EXTRA.get(key) || null
}

export function getOverlayNote(name) {
  const frame = getFrame(name)
  if (!frame) return null
  if (frame.overlayNote) return frame.overlayNote
  return OVERLAYS[frame.overlay] || null
}

/** @internal tests */
export function _clearExtraFrames() {
  EXTRA.clear()
}
