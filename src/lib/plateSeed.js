/** Last gathered ingredient, or the workspace focus when the dish is empty. */
export function plateSeed(dish, focusIngredient) {
  const names = (dish || []).map((d) => d?.name).filter(Boolean)
  if (names.length) return names[names.length - 1]
  const focus = String(focusIngredient || '').trim()
  return focus || null
}
