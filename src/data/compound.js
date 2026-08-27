/**
 * Compound lens — Foodb ingredient families.
 * Kept as a thin re-export so existing imports keep working; groups are
 * generated from the full ingredient list at call time.
 */
export { compoundGroups as buildCompoundGroups } from './ingredients.js'

/** @deprecated Prefer compoundGroups(focus) — static duck groups removed. */
export const COMPOUND_GROUPS = []
