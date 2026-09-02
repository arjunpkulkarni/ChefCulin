import { useEffect, useState } from 'react'
import { useWorkspace } from '../context/WorkspaceContext.jsx'
import { bestTraditionMatches, getDishDetail } from '../lib/traditionDb.js'
import OptionCard from './OptionCard.jsx'
import Chip from './Chip.jsx'

export default function TraditionPane() {
  const { cuisineScope, overlayNote, form, focusIngredient, addIngredient, dish } = useWorkspace()
  const [status, setStatus] = useState({ kind: 'loading', text: 'Loading tradition matches…' })
  const [rationale, setRationale] = useState('')
  const [options, setOptions] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [busy, setBusy] = useState(false)

  const dishKey = dish.map((d) => d.name).join('|')

  useEffect(() => {
    setSelectedId(null)
    setDetail(null)
  }, [focusIngredient, cuisineScope])

  useEffect(() => {
    if (!focusIngredient) {
      setStatus({ kind: 'empty', text: 'Choose a focus ingredient to load tradition matches.' })
      setOptions([])
      return
    }

    let cancelled = false
    setBusy(true)
    setStatus({ kind: 'loading', text: 'Loading tradition matches…' })
    ;(async () => {
      try {
        const plateNames = dish.map((d) => d.name)
        const rows = await bestTraditionMatches({
          focus: focusIngredient,
          names: plateNames,
          cuisine: cuisineScope?.label,
          cuisineScope,
          limit: 5,
        })
        if (cancelled) return
        setOptions(rows)
        const plate = plateNames.length
          ? `${focusIngredient} plus ${plateNames.join(', ')}`
          : focusIngredient
        setRationale(
          rows.length
            ? `Five Tradition-DB dishes featuring ${focusIngredient}. Cards that share more of your gathered plate rank higher; cuisine scope only widens the pool when needed.`
            : `No Tradition-DB rows mention ${focusIngredient}.`
        )
        setStatus({
          kind: rows.length ? 'ok' : 'empty',
          text: rows.length ? `${rows.length} documented match${rows.length === 1 ? '' : 'es'}` : 'No matching records',
        })
      } catch (err) {
        if (cancelled) return
        setOptions([])
        setRationale('')
        setStatus({ kind: 'err', text: err?.message || String(err) })
      } finally {
        if (!cancelled) setBusy(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [focusIngredient, dishKey, cuisineScope, dish])

  async function onSelectOption(option) {
    if (busy) return
    setBusy(true)
    setSelectedId(option.id)
    setStatus({ kind: 'loading', text: 'Loading dish detail…' })
    try {
      const full = await getDishDetail({ record_id: option.id })
      if (!full) {
        setStatus({ kind: 'err', text: `No detail for ${option.id}` })
        setDetail(null)
        return
      }
      setDetail(full)
      const companions = full.companionIngredients || []
      setStatus({
        kind: 'ok',
        text:
          companions.length > 0
            ? `${companions.length} companion ingredient${companions.length === 1 ? '' : 's'} on file — none added yet`
            : 'Opened — no companion ingredients on file',
      })
    } catch (err) {
      setStatus({ kind: 'err', text: err?.message || String(err) })
    } finally {
      setBusy(false)
    }
  }

  function onCommitCompanions() {
    const companions = detail?.companionIngredients || []
    if (!companions.length) return
    for (const name of companions) {
      addIngredient(name, 'tradition')
    }
    setStatus({
      kind: 'ok',
      text: `Added ${companions.length} companion ingredient${companions.length === 1 ? '' : 's'} to the dish`,
    })
  }

  return (
    <section className="pane pane-t on">
      <p className="pane-intro">
        Documented dishes that feature <strong>{focusIngredient}</strong>
        {dish.length ? ' — ranked by how many other gathered ingredients they share' : ''}.
        Pick a card to read the dish; add its companions individually or all at once.
      </p>

      {/* §2.7 disclosure — and §2.6: Pending is unassessed, not Low. */}
      <div className="lens-source">
        <span className="ls-lbl">Source</span>
        Tradition database — documented dishes with cited sources. Matches are limited to dishes
        where the ingredient is a main, seasoning, aromatic or listed ingredient, so a dish does not
        qualify merely for being cooked in it.
      </div>

      {cuisineScope && (
        <div className="scope-lens-note">
          <span className="sn-lbl">Cuisine scope · {cuisineScope.label}</span>
          Matches prefer this region when the database has one.
        </div>
      )}
      {form && overlayNote && (
        <div className="overlay-note">
          <span className="on-lbl">Form overlay · {form.name}</span>
          {overlayNote}
        </div>
      )}

      {status.kind !== 'idle' && (
        <div
          className={`notice ${status.kind === 'ok' ? 'ok' : status.kind === 'err' ? 'err' : ''}`}
        >
          {status.text}
        </div>
      )}

      {rationale && <p className="agent-rationale">{rationale}</p>}

      {options.length > 0 && (
        <div className="option-grid">
          {options.map((o) => (
            <OptionCard
              key={o.id}
              option={o}
              selected={selectedId === o.id}
              onSelect={onSelectOption}
              disabled={busy}
              stamp={{
                label: o.confidenceIsAssessed
                  ? `${o.confidence} confidence · ${o.sourceCount} source${o.sourceCount === 1 ? '' : 's'}`
                  : `Unassessed · ${o.sourceCount} source${o.sourceCount === 1 ? '' : 's'}`,
                title: o.confidenceIsAssessed
                  ? `${o.id} — confidence ${o.confidence}`
                  : `${o.id} — confidence not yet assessed (this is not the same as low)`,
              }}
              className={o.confidenceIsAssessed ? '' : 'conf-pending'}
            />
          ))}
        </div>
      )}

      {detail && (
        <div className="tradition-detail">
          <div className="g-label">
            {detail.item}
            {detail.traditionality_class && (
              <span className="posture p-doc">{detail.traditionality_class}</span>
            )}
          </div>
          <div className="g-why">
            {[detail.cuisine, detail.country, detail.region_or_community, detail.source_thread]
              .filter(Boolean)
              .join(' · ')}
          </div>
          {detail.preparation_or_function && (
            <p className="pane-intro">{detail.preparation_or_function}</p>
          )}
          {detail.historical_or_cultural_note && (
            <p className="pane-intro">{detail.historical_or_cultural_note}</p>
          )}
          <div className="g-label">Companions on the dish</div>
          <div className="chips">
            {(detail.companionIngredients || []).map((name) => (
              <Chip key={name} name={name} lens="tradition" />
            ))}
          </div>
          {(detail.companionIngredients || []).length > 0 && (
            <button type="button" className="mini" onClick={onCommitCompanions}>
              Add all {detail.companionIngredients.length} to the dish
            </button>
          )}
        </div>
      )}

      <div className="closer">
        Opening a card only reads it — nothing reaches the sidebar dish list until you add a
        companion, either by tapping one or with the add-all button.
      </div>
    </section>
  )
}
