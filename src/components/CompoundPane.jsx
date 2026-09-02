import { useEffect, useState } from 'react'
import { useWorkspace } from '../context/WorkspaceContext.jsx'
import * as api from '../api.js'
import { plateSeed } from '../lib/plateSeed.js'
import { resolveIngredient } from '../lib/spineResolve.js'
import { groupsFor, sharedCompoundSentence, topCompounds } from '../lib/compoundLanguage.js'
import Chip from './Chip.jsx'

/** Strip the VCF binomial so a chef reads "Pork", not "PORK (Sus scrofa L.)". */
function neighborLabel(raw) {
  return String(raw || '')
    .replace(/\s*\([A-Z][a-z]+ (?:[a-z]+|species)[^)]*\)/g, '')
    .trim()
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function CompoundPane() {
  const { dish, cuisineScope, overlayNote, form, focusIngredient } = useWorkspace()
  const [status, setStatus] = useState({ kind: 'loading', text: 'Loading compound layer…' })
  const [resolution, setResolution] = useState(null)
  const [rows, setRows] = useState([])
  const [openRow, setOpenRow] = useState(null)

  useEffect(() => {
    const display = plateSeed(dish, focusIngredient)
    if (!display) {
      setStatus({
        kind: 'empty',
        text: 'Choose a focus ingredient or gather one on the plate to seed the compound layer.',
      })
      setRows([])
      setResolution(null)
      return
    }

    // Resolution happens here, deterministically, before anything is fetched —
    // never inside the request. See src/lib/spineResolve.js.
    const r = resolveIngredient(display)
    setResolution(r)

    if (r.state !== 'resolved') {
      setRows([])
      setStatus({
        kind: 'empty',
        text:
          r.state === 'ambiguous'
            ? `“${display}” names more than one ingredient in the compound corpus — pick one.`
            : `No VCF compound data for “${display}”.`,
      })
      return
    }

    let cancelled = false
    setStatus({ kind: 'loading', text: `Loading shared compounds for ${r.display}…` })
    ;(async () => {
      try {
        const res = await api.vcfPairs(r.spine_id, 24)
        if (cancelled) return
        const inDish = new Set(dish.map((d) => d.name.toLowerCase()))
        const kept = (res.results || [])
          .map((row) => ({ ...row, label: neighborLabel(row.match_raw_name) }))
          .filter((row) => !inDish.has(row.label.toLowerCase()))
        setRows(kept)
        setStatus({
          kind: kept.length ? 'ok' : 'empty',
          text: kept.length
            ? `${kept.length} ingredient${kept.length === 1 ? '' : 's'} share volatile compounds with ${r.display}`
            : `No shared-compound neighbours for ${r.display}`,
        })
      } catch (err) {
        if (cancelled) return
        setRows([])
        setStatus({
          kind: 'err',
          text: `Compound API unreachable. Start: npm run api — ${err.message || err}`,
        })
      }
    })()
    return () => {
      cancelled = true
    }
  }, [dish, focusIngredient])

  return (
    <section className="pane pane-c on">
      <div className={`notice ${status.kind === 'ok' ? 'ok' : status.kind === 'err' ? 'err' : ''}`}>
        {status.kind === 'ok' ? (
          <>
            <strong>Compound layer.</strong> {status.text}
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
        Ingredients that share <em>volatile aroma compounds</em> with{' '}
        {resolution?.display || focusIngredient}. Each one names the compound families behind the
        match — the evidence, not a similarity number.
      </p>

      {/* §2.7 disclosure — every lens states what it read from. */}
      <div className="lens-source">
        <span className="ls-lbl">Source</span>
        Volatile Compounds in Food (VCF), licensed. Shared-compound counts weighted by how rare
        each compound is across the corpus.
        {resolution?.state === 'resolved' && (
          <> Resolved “{resolution.query}” → {resolution.spine_member} via {resolution.matched_on} match.</>
        )}
      </div>

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
        </div>
      )}

      <div className="group">
        <div className="g-label">
          Shared volatile compounds{' '}
          <span className="posture p-doc">{resolution?.display || focusIngredient}</span>
        </div>

        <div className="compound-rows">
          {rows.map((row) => {
            const shared = row.top_shared_compounds || []
            const sentence = sharedCompoundSentence(shared)
            const open = openRow === row.match_vcf_product_id
            return (
              <div className="compound-row" key={row.match_vcf_product_id}>
                <div className="cr-head">
                  <Chip name={row.label} lens="compound" />
                  <span className="cr-shared">{row.shared_count} shared compounds</span>
                </div>
                {sentence && <div className="cr-why">{sentence}.</div>}
                <button
                  type="button"
                  className="mini"
                  onClick={() => setOpenRow(open ? null : row.match_vcf_product_id)}
                >
                  {open ? 'Hide compounds' : 'Show compounds'}
                </button>
                {open && (
                  <div className="cr-detail">
                    <div className="g-label">Groups</div>
                    <div className="cr-groups">
                      {groupsFor(shared).map((g) => (
                        <span className="cr-group" key={g.group}>
                          {g.phrase} <span className="chip-meta">{g.count}</span>
                        </span>
                      ))}
                    </div>
                    <div className="g-label">Most distinctive compounds</div>
                    <ul className="cr-compounds">
                      {topCompounds(shared, { limit: 6 }).map((c) => (
                        <li key={c.compound_id || c.raw_compound}>
                          {c.raw_compound}
                          <span className="chip-meta">
                            {c.compound_group} · in {c.df_culinary} corpus ingredients
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )
          })}
          {status.kind === 'ok' && !rows.length && (
            <div className="no-modes">No shared-compound neighbours for this seed.</div>
          )}
        </div>
      </div>

      <div className="closer">
        Seeded from{' '}
        {dish.length ? 'the last ingredient on your plate' : `your focus — ${focusIngredient}`}.
        Rarer shared compounds count for more, so a long list of common ones ranks below a short
        list of distinctive ones.
      </div>
    </section>
  )
}
