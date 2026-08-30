const KEY = 'culinai.user'
const FALLBACK = 'chef-local'

/**
 * Palate Memory is per-user, but there is no auth in this prototype. So a chef
 * gets a stable id generated on first use and kept in localStorage — enough to
 * keep one browser's kept dishes separate from another's, and honest about
 * being nothing more than that.
 *
 * Falls back to a shared id where storage is unavailable (private windows,
 * blocked cookies) rather than throwing: losing per-browser separation is a
 * smaller failure than losing Save entirely.
 */
export function localUserId() {
  try {
    const existing = window.localStorage.getItem(KEY)
    if (existing) return existing
    const id = `chef-${
      window.crypto?.randomUUID?.() || Math.random().toString(36).slice(2, 12)
    }`
    window.localStorage.setItem(KEY, id)
    return id
  } catch {
    return FALLBACK
  }
}
