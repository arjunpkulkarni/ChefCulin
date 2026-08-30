import { useWorkspace } from '../context/WorkspaceContext.jsx'

export default function FormPane() {
  const { form, commitForm, focusIngredient, formCatalog } = useWorkspace()
  const { loading, forms, source, error, rationale } = formCatalog

  if (!focusIngredient) {
    return (
      <section className="pane pane-f on">
        <div className="notice">Choose a focus ingredient in the mast — form frames load from the LLM for that ingredient.</div>
      </section>
    )
  }

  return (
    <section className="pane pane-f on">
      <p className="pane-intro">
        Preparation states for {focusIngredient}
        {forms.length ? ` — ${forms.length} frames from ${source === 'llm' ? 'the LLM' : source}` : ''}.
        Commit to one if it clarifies the plate.
      </p>

      {loading && <div className="notice">Generating process frames for {focusIngredient}…</div>}
      {error && (
        <div className="notice err">
          <strong>Form lens unavailable.</strong> {error} Set <code>VITE_OPENAI_API_KEY</code> in{' '}
          <code>.env</code> and restart <code>npm run dev</code>.
        </div>
      )}
      {rationale && !loading && <p className="agent-rationale">{rationale}</p>}

      {forms.map((f) => (
        <FrameCard key={f.name} card={f} active={form?.name === f.name} onCommit={commitForm} />
      ))}

      {!loading && !error && !forms.length && (
        <div className="notice">No form frames returned — try another focus ingredient.</div>
      )}

      <div className="closer">
        Form answers state and process for this ingredient. Ingredients still gather from the other
        lenses (compound network, corpus, tradition DB).
      </div>
    </section>
  )
}

function FrameCard({ card, active, onCommit }) {
  return (
    <div className="group">
      <div className="g-label">{card.title || card.name}</div>
      {card.desc && <div className="g-why">{card.desc}</div>}
      {card.craft.map((row) => (
        <div className="craft-row" key={row.k}>
          <span className="ck">{row.k}</span>
          <span className="cv">{row.v}</span>
        </div>
      ))}
      <button
        type="button"
        className={`commitf${active ? ' on' : ''}`}
        onClick={() => onCommit(card.name, card.desc)}
      >
        {active ? 'Committed' : 'Commit this form'}
      </button>
    </div>
  )
}
