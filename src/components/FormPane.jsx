import { formsForIngredient } from '../data/formCards.js'
import { useWorkspace } from '../context/WorkspaceContext.jsx'

export default function FormPane() {
  const { form, commitForm, focusIngredient } = useWorkspace()
  const cards = formsForIngredient(focusIngredient)

  return (
    <section className="pane pane-f on">
      <p className="pane-intro">
        Preparation states that fit {focusIngredient}
        {cards[0] ? ` — ${cards.length} process frames for this kind of ingredient` : ''}. Commit
        to one if it clarifies the plate.
      </p>
      {cards.map((f) => (
        <FrameCard key={f.name} card={f} active={form?.name === f.name} onCommit={commitForm} />
      ))}
      <div className="closer">
        Form answers state and process for this ingredient family. Ingredients still gather from
        the other lenses.
      </div>
    </section>
  )
}

function FrameCard({ card, active, onCommit }) {
  return (
    <div className="group">
      <div className="g-label">{card.title || card.name}</div>
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
