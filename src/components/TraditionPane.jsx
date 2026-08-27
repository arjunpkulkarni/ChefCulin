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
    let cancelled = false
    setBusy(true)
    setStatus({ kind: 'loading', text: 'Loading tradition matches…' })
    ;(async () => {
      try {
        const names = [focusIngredient, ...dish.map((d) => d.name)]
        const rows = await bestTraditionMatches({
          names,
          cuisine: cuisineScope?.label,
          cuisineScope,
          limit: 5,
        })
        if (cancelled) return
        setOptions(rows)
        const plate = dish.length
          ? `${focusIngredient} plus ${dish.map((d) => d.name).join(', ')}`
          : focusIngredient
        setRationale(
          rows.length
            ? `Five strongest Tradition-DB matches for ${plate}. Ranked by how many of those names appear as companions or in the dish text, then by documented traditionality.`
            : `No Tradition-DB rows mention ${plate}.`
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
      for (const name of companions) {
        addIngredient(name, 'tradition')
      }
      setStatus({
        kind: 'ok',
        text:
          companions.length > 0
            ? `Added ${companions.length} companion ingredient${companions.length === 1 ? '' : 's'} to the dish`
            : 'Selected — no companion ingredients on file',
      })
    } catch (err) {
      setStatus({ kind: 'err', text: err?.message || String(err) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="pane pane-t on">
      <p className="pane-intro">
        Documented dishes that mention {focusIngredient}
        {dish.length ? ' and what you have already gathered' : ''}. These five are loaded from the
        Tradition database — pick a card to pull its companion ingredients onto the plate.
      </p>

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
                label: o.plateHits ? `${o.plateHits} plate hit${o.plateHits === 1 ? '' : 's'}` : 'Tradition DB',
                title: o.id,
              }}
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
        </div>
      )}

      <div className="closer">
        Selecting a card commits every companion ingredient into the sidebar dish list. Remove any
        you don&apos;t want from there.
      </div>
    </section>
  )
}
