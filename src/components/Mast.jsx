import { useEffect, useRef, useState } from 'react'
import { useWorkspace } from '../context/WorkspaceContext.jsx'
import { searchIngredients } from '../data/ingredients.js'

export default function Mast() {
  const {
    focusIngredient,
    setFocusIngredient,
    cuisineScope,
    scopeMenuOpen,
    setScopeMenuOpen,
    regionPicks,
    lockCuisine,
    clearCuisine,
    lockCuisineFromInput,
  } = useWorkspace()
  const [input, setInput] = useState('')
  const [focusQuery, setFocusQuery] = useState('')
  const [focusOpen, setFocusOpen] = useState(false)
  const ctrl = useRef(null)
  const focusCtrl = useRef(null)

  useEffect(() => {
    const onDoc = (e) => {
      if (ctrl.current && !ctrl.current.contains(e.target)) setScopeMenuOpen(false)
      if (focusCtrl.current && !focusCtrl.current.contains(e.target)) setFocusOpen(false)
    }
    document.addEventListener('click', onDoc)
    return () => document.removeEventListener('click', onDoc)
  }, [setScopeMenuOpen])

  const focusHits = searchIngredients(focusQuery, { limit: 30 })

  return (
    <div className="mast">
      <div className="brand">
        Culin<span>AI</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div className="focus-control" ref={focusCtrl}>
          <span className="scope-lbl">Focus ingredient</span>
          <button
            type="button"
            className="focus-btn"
            onClick={() => setFocusOpen((o) => !o)}
            aria-expanded={focusOpen}
          >
            {focusIngredient}
          </button>
          {focusOpen && (
            <div className="focus-menu">
              <input
                type="search"
                value={focusQuery}
                autoFocus
                placeholder="Search Foodb list (933)…"
                onChange={(e) => setFocusQuery(e.target.value)}
                aria-label="Search focus ingredient"
              />
              <div className="focus-hits">
                {focusHits.map((name) => (
                  <button
                    key={name}
                    type="button"
                    className={`focus-hit${name === focusIngredient ? ' on' : ''}`}
                    onClick={() => {
                      setFocusIngredient(name)
                      setFocusOpen(false)
                      setFocusQuery('')
                    }}
                  >
                    {name}
                  </button>
                ))}
                {!focusHits.length && <div className="focus-empty">No matches</div>}
              </div>
            </div>
          )}
        </div>
        <div className="scope-control" ref={ctrl}>
          <button
            type="button"
            className={`scope-btn${cuisineScope ? ' locked' : ''}`}
            onClick={() => setScopeMenuOpen((o) => !o)}
          >
            <span className="scope-lbl">Cuisine scope</span>
            <span>{cuisineScope ? cuisineScope.label : 'None'}</span>
            {cuisineScope && (
              <span
                className="scope-x"
                onClick={(e) => {
                  e.stopPropagation()
                  clearCuisine()
                }}
              >
                ✕
              </span>
            )}
          </button>
          <div className={`scope-menu${scopeMenuOpen ? ' open' : ''}`}>
            <div className="scope-menu-lbl">Lock to a documented region</div>
            <div className="scope-picks">
              {regionPicks.map((p) => (
                <button
                  key={p.key}
                  type="button"
                  className="scope-pick"
                  onClick={() => lockCuisine(p.key, p.label)}
                >
                  {p.label}
                </button>
              ))}
            </div>
            <div className="scope-menu-note">
              Only regions with a real documented thread are listed above. Type anything else
              below — if it isn&apos;t documented yet, you&apos;ll get an honest answer, not a
              guess.
            </div>
            <div className="scope-input-row">
              <input
                type="text"
                value={input}
                placeholder="e.g. India, Malabar, Latin/Caribbean…"
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    lockCuisineFromInput(input)
                    setInput('')
                  }
                }}
              />
              <button
                type="button"
                onClick={() => {
                  lockCuisineFromInput(input)
                  setInput('')
                }}
              >
                Lock
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
