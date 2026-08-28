import { useEffect, useState } from 'react'
import { useWorkspace } from '../context/WorkspaceContext.jsx'
import * as api from '../api.js'
import { plateSeed } from '../lib/plateSeed.js'
import { matchRecipeNlg } from '../lib/matchRecipeNlg.js'
import Chip from './Chip.jsx'

export default function CooccurPane() {
  const { dish, cuisineScope, focusIngredient } = useWorkspace()
  const [status, setStatus] = useState({ kind: 'loading', text: 'Connecting to corpus API…' })
  const [seed, setSeed] = useState('')
  const [matchMeta, setMatchMeta] = useState(null)
  const [neighbors, setNeighbors] = useState([])
  const [techs, setTechs] = useState([])
  const [why, setWhy] = useState('')

  useEffect(() => {
    const display = plateSeed(dish, focusIngredient)
    if (!display) {
      setStatus({
        kind: 'empty',
        text: 'Choose a focus ingredient or gather one on the plate to seed the corpus.',
      })
      setNeighbors([])
      setTechs([])
      return
    }

    let cancelled = false
    setStatus({ kind: 'loading', text: `Resolving RecipeNLG token for “${display}”…` })
    ;(async () => {
      try {
        const matched = await matchRecipeNlg(display)
        if (cancelled) return
        const canonical = matched.canonical
        setMatchMeta({ display, canonical, source: matched.source })
        setStatus({ kind: 'loading', text: `Loading corpus neighbors for ${canonical}…` })

        const [health, co, tech] = await Promise.all([
          api.health(),
          api.cooccur(canonical, 24),
          api.techniques(canonical, 8),
        ])
        if (cancelled) return
        const inDish = new Set(dish.map((d) => d.name))
        const rows = (co.results || [])
          .filter((r) => !inDish.has(r.ingredient) && !HUBS.has(r.ingredient))
          .slice(0, 16)
        const canon = co.canonical || canonical
        setSeed(canon)
        setNeighbors(rows)
        setTechs(tech.results || [])
        const via = `RecipeNLG token “${canon}” (${matched.source} from “${display}”)`
        setWhy(
          `${via}. Neighbors from precomputed NPMI tables` +
            (health.cooccur_edges
              ? ` (${health.cooccur_edges.toLocaleString()} edges)`
              : '') +
            '. Chip suffix = confidence ×100. Hubs like salt/butter filtered for display.'
        )
        setStatus({
          kind: 'ok',
          text: `Live corpus. Serving artifact tables${health.palate_db ? ' + Palate DB' : ''}.`,
        })
      } catch (err) {
        if (cancelled) return
        setNeighbors([])
        setTechs([])
        setStatus({
          kind: 'err',
          text: `Corpus API unreachable. Start: npm run demo (or npm run api) — ${err.message || err}`,
        })
      }
    })()
    return () => {
      cancelled = true
    }
  }, [dish, focusIngredient])

  return (
    <section className="pane pane-o on">
      <div className={`notice ${status.kind === 'ok' ? 'ok' : status.kind === 'err' ? 'err' : ''}`}>
        {status.kind === 'ok' ? (
          <>
            <strong>Live corpus.</strong> {status.text.replace(/^Live corpus\.\s*/, '')}
          </>
        ) : status.kind === 'err' ? (
          <>
            <strong>Corpus API unreachable.</strong> {status.text.replace(/^Corpus API unreachable\.\s*/, '')}
          </>
        ) : (
          status.text
        )}
      </div>

      {cuisineScope && (
        <div className="scope-lens-note">
          <span className="sn-lbl">Cuisine scope locked · {cuisineScope.label}</span>
          Corpus patterns aren&apos;t regional — this lens stays fully unfiltered.
        </div>
      )}

      <div className="cooccur-live">
        <div className="group">
          <div className="g-label">
            Corpus neighbors{' '}
            <span className="posture p-corp">{status.kind === 'loading' ? 'loading' : seed || '—'}</span>
          </div>
          <div className="g-why">{why || 'Live co-occurrence from RecipeNLG artifact tables (NPMI).'}</div>
          <div className="chips">
            {neighbors.map((r) => (
              <Chip
                key={r.ingredient}
                name={r.ingredient}
                lens="co-occurrence"
                meta={Math.round((r.confidence || 0) * 100)}
              />
            ))}
            {status.kind === 'ok' && !neighbors.length && (
              <div className="no-modes">No non-hub neighbors for {seed}.</div>
            )}
          </div>
        </div>
        {!!techs.length && (
          <div className="group">
            <div className="g-label">
              Associated techniques <span className="posture p-corp">corpus</span>
            </div>
            <div className="g-why">
              How this ingredient shows up in instruction text — frequency as confidence, not a
              prescription.
            </div>
            <div className="chips tech-chips">
              {techs.map((t) => (
                <span className="chip" key={t.technique}>
                  <span className="plus">·</span>
                  {t.technique}
                  <span className="chip-meta">
                    {Math.round((t.confidence || 0) * 100)} · n={t.freq}
                  </span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="closer">
        Seeded from {dish.length ? 'the last ingredient on your plate' : `your focus — ${focusIngredient}`}
        {matchMeta ? ` → RecipeNLG “${matchMeta.canonical}” (${matchMeta.source})` : ''}. Neighbors
        come from the RecipeNLG corpus only.
      </div>
    </section>
  )
}

const HUBS = new Set([
  'salt',
  'butter',
  'sugar',
  'water',
  'pepper',
  'black pepper',
  'oil',
  'olive oil',
  'vegetable oil',
  'flour',
  'egg',
  'eggs',
  'onion',
  'garlic',
])
