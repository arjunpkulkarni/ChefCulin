import { useEffect, useState } from 'react'
import { COOCCUR_STAGED } from '../data/cooccurStaged.js'
import { useWorkspace } from '../context/WorkspaceContext.jsx'
import * as api from '../api.js'
import Chip from './Chip.jsx'
import ChipGroup from './ChipGroup.jsx'

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

export default function CooccurPane() {
  const { dish, cuisineScope } = useWorkspace()
  const [status, setStatus] = useState({ kind: 'loading', text: 'Connecting to corpus API…' })
  const [seed, setSeed] = useState('duck')
  const [neighbors, setNeighbors] = useState([])
  const [techs, setTechs] = useState([])
  const [why, setWhy] = useState('')

  useEffect(() => {
    const s = dish.length ? dish[dish.length - 1].name : 'duck'
    let cancelled = false
    setStatus({ kind: 'loading', text: `Loading corpus neighbors for ${s}…` })
    ;(async () => {
      try {
        const [health, co, tech] = await Promise.all([
          api.health(),
          api.cooccur(s, 24),
          api.techniques(s, 8),
        ])
        if (cancelled) return
        const inDish = new Set(dish.map((d) => d.name))
        const rows = (co.results || [])
          .filter((r) => !inDish.has(r.ingredient) && !HUBS.has(r.ingredient))
          .slice(0, 16)
        setSeed(co.canonical || s)
        setNeighbors(rows)
        setTechs(tech.results || [])
        setWhy(
          `Neighbors of ${co.canonical || s} from precomputed NPMI tables` +
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
          text: `Corpus API unreachable. Start: cd pipeline && python -m culin_etl.serve — ${err.message || err}`,
        })
      }
    })()
    return () => {
      cancelled = true
    }
  }, [dish])

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
            <span className="posture p-corp">{status.kind === 'loading' ? 'loading' : seed}</span>
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

      <p className="pane-intro" style={{ marginTop: '1.5rem' }}>
        Staged functional communities (below) stay as design framing. Live neighbors above are
        the wired corpus.
      </p>
      {COOCCUR_STAGED.map((g, i) => (
        <ChipGroup key={g.title} group={g} id={`o-${i}`} />
      ))}
      <div className="closer">
        These are jobs that keep reappearing around duck — not the ingredients duck is
        &quot;most often&quot; paired with.
      </div>
    </section>
  )
}
