/**
 * Phase-behaviour render path (§2.5).
 *
 * Two modes, and the difference between them is the whole point:
 *
 *   framed     — an authored sentence in phase_frames.jsonl fired. Render it
 *                verbatim.
 *   data_only  — no sentence. Render the facts and stop.
 *
 * There is deliberately no fallback sentence for data_only. A generic default
 * ("these may compete") would satisfy the letter of "no sentence outside
 * phase_frames.jsonl" while doing exactly the damage that rule exists to
 * prevent: the chef sees an alert they cannot interpret, cannot act on, and
 * learns to dismiss the whole category. An unexplained warning is worse than
 * showing more detail, or showing none.
 */

/** Percentiles at or above this are worth naming as unusually high. */
const NOTABLE_PERCENTILE = 90

function pct(x) {
  return x == null ? null : `${Math.round(x * 100)}%`
}

function label(raw) {
  return String(raw || '')
    .replace(/\s*\([A-Z][a-z]+ (?:[a-z]+|species)[^)]*\)/g, '')
    .trim()
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/** How a group share reads against the corpus: 'top 10%' etc, or null. */
export function percentileNote(percentile) {
  if (percentile == null) return null
  if (percentile >= 99) return 'top 1% of corpus'
  if (percentile >= NOTABLE_PERCENTILE) return `top ${100 - Math.floor(percentile)}% of corpus`
  return null
}

/**
 * Turn one competition row into something renderable.
 *
 * @returns {{mode: 'framed'|'data_only', sentence: string|null, facts: object[]}}
 */
export function renderPhaseRow(row) {
  if (!row) return null
  const framed = row.render_mode === 'framed' && Boolean(row.sentence)

  const facts = []
  for (const side of ['a', 'b']) {
    const share = row[`${side}_group_share`]
    if (share == null) continue
    facts.push({
      component: label(row[`dish_component_${side}`]),
      group: row[`${side}_group`],
      share: pct(share),
      percentile: row[`${side}_group_percentile`],
      note: percentileNote(row[`${side}_group_percentile`]),
      baseline: pct(row[`${side}_group_baseline_median`]),
    })
  }

  return {
    mode: framed ? 'framed' : 'data_only',
    // Verbatim when framed; null otherwise. Never a substitute.
    sentence: framed ? row.sentence : null,
    frame_id: framed ? row.frame_id : null,
    bucket: row.bucket,
    conflict_type: row.conflict_type,
    facts,
  }
}

/**
 * One plain-language line describing the facts of a data_only row, built only
 * from numbers present in the row. This is a rendering of data, not an authored
 * claim: it names shares and percentiles and asserts nothing about what the
 * chef should do. Returns null when there are no numbers to state.
 */
export function dataOnlyLine(rendered) {
  if (!rendered || rendered.mode !== 'data_only') return null
  const parts = rendered.facts
    .filter((f) => f.share)
    .map((f) => {
      const tail = f.note ? ` (${f.note})` : ''
      return `${f.component} ${f.share} ${String(f.group || '').toLowerCase()}${tail}`
    })
  if (!parts.length) return null
  return parts.join(', ')
}

/** Rows worth surfacing first: framed ones, then the most extreme percentiles. */
export function rankPhaseRows(rows = []) {
  return [...rows]
    .map(renderPhaseRow)
    .filter(Boolean)
    .sort((x, y) => {
      if (x.mode !== y.mode) return x.mode === 'framed' ? -1 : 1
      const px = Math.max(...x.facts.map((f) => f.percentile || 0), 0)
      const py = Math.max(...y.facts.map((f) => f.percentile || 0), 0)
      return py - px
    })
}
