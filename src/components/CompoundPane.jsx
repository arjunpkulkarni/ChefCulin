import { useEffect, useState } from 'react'
import { useWorkspace } from '../context/WorkspaceContext.jsx'
import * as api from '../api.js'
import { plateSeed } from '../lib/plateSeed.js'
import Chip from './Chip.jsx'

export default function CompoundPane() {
  const { dish, cuisineScope, overlayNote, form, focusIngredient } = useWorkspace()
  const [status, setStatus] = useState({ kind: 'loading', text: 'Loading flavor compound network…' })
  const [seed, setSeed] = useState('')
  const [neighbors, setNeighbors] = useState([])
  const [why, setWhy] = useState('')

  useEffect(() => {
    const display = plateSeed(dish, focusIngredient)
    if (!display) {
      setStatus({
        kind: 'empty',
        text: 'Choose a focus ingredient or gather one on the plate to seed the compound network.',
      })
      setNeighbors([])
      return
    }

    let cancelled = false
    setStatus({ kind: 'loading', text: `Ranking shared volatile compounds for “${display}”…` })
    ;(async () => {
      try {
        const [health, res] = await Promise.all([
          api.health(),
          api.compound(display, 24),
        ])
        if (cancelled) return
        const inDish = new Set(dish.map((d) => d.name.toLowerCase()))
        const rows = (res.results || []).filter(
          (r) =>
            !inDish.has(r.display?.toLowerCase()) &&
            !inDish.has(r.ingredient?.toLowerCase())
        )
        setSeed(res.canonical || display)
        setNeighbors(rows)
        setWhy(
          `Flavor-network projection (Ahn et al. / FooDB). Edge weight = shared volatile compounds.` +
            (health.compound_edges
              ? ` ${health.compound_edges.toLocaleString()} precomputed neighbor rows.`
              : '') +
            ' Chip suffix = normalized compound overlap ×100.'
        )
        setStatus({
          kind: rows.length ? 'ok' : 'empty',
          text: rows.length
            ? `${rows.length} compound-ranked neighbor${rows.length === 1 ? '' : 's'} for ${res.canonical || display}`
            : `No flavor-network match for “${display}”`,
        })
      } catch (err) {
        if (cancelled) return
        setNeighbors([])
        setStatus({
          kind: 'err',
          text: `Compound API unreachable. Start: npm run demo (or npm run api) — ${err.message || err}`,
        })
      }
    })()
    return () => {
      cancelled = true
    }
  }, [dish, focusIngredient])

  return (
    <section className="pane pane-c on">
      <div
        className={`notice ${status.kind === 'ok' ? 'ok' : status.kind === 'err' ? 'err' : status.kind === 'empty' ? '' : ''}`}
      >
        {status.kind === 'ok' ? (
          <>
            <strong>Flavor compound network.</strong> {status.text}
          </>
        ) : status.kind === 'err' ? (
          <>
            <strong>Compound lens unavailable.</strong> {status.text}
          </>
        ) : (
          status.text
        )}
      </div>

      <p className="pane-intro">
        Ingredients ranked by <em>shared volatile compounds</em> with {focusIngredient} — not an
        alphabetical Foodb browse. Stronger overlap = more shared aroma chemistry (vendored
        flavor-network graph).
      </p>

      {cuisineScope && (
        <div className="scope-lens-note">
          <span className="sn-lbl">Cuisine scope locked · {cuisineScope.label}</span>
          Compound chemistry isn&apos;t regional — scope does not filter this lens.
        </div>
      )}
      {form && overlayNote && (
        <div className="overlay-note">
          <span className="on-lbl">Form overlay · {form.name}</span>
          {overlayNote}
          <span className="on-foot">Applies across lenses — delivery and placement shift with form.</span>
        </div>
      )}

      <div className="group">
        <div className="g-label">
          Shared volatile compounds{' '}
          <span className="posture p-est">{status.kind === 'loading' ? 'loading' : seed || focusIngredient}</span>
        </div>
        <div className="g-why">{why || 'Loading compound overlap scores…'}</div>
        <div className="chips">
          {neighbors.map((r) => (
            <Chip
              key={r.ingredient}
              name={r.display || r.ingredient}
              lens="compound"
              meta={Math.round((r.confidence || 0) * 100)}
            />
          ))}
          {status.kind === 'ok' && !neighbors.length && (
            <div className="no-modes">No compound neighbors for this seed in the flavor network.</div>
          )}
        </div>
      </div>

      <div className="closer">
        Seeded from {dish.length ? 'the last ingredient on your plate' : `your focus — ${focusIngredient}`}
        {seed ? ` → network token “${seed}”` : ''}. Co-occurrence still comes from the RecipeNLG corpus.
      </div>
    </section>
  )
}
