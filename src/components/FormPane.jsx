import { FORM_CARDS } from '../data/formCards.js'
import { useWorkspace } from '../context/WorkspaceContext.jsx'

export default function FormPane() {
  const { form, commitForm } = useWorkspace()
  const primary = FORM_CARDS.slice(0, 5)
  const redMeat = FORM_CARDS.slice(5)

  return (
    <section className="pane pane-f on">
      <p className="pane-intro">
        Across documented threads, duck has been made into very different things. These
        aren&apos;t options to pick from — they&apos;re states cooks have arrived at. Commit
        to one if it clarifies the dish.
      </p>
      {primary.map((f) => (
        <FrameCard key={f.name} card={f} active={form?.name === f.name} onCommit={commitForm} />
      ))}
      <div className="g-section">If duck is red meat…</div>
      <p className="pane-intro">
        The magret insight isn&apos;t just about searing. Once the bird is treated as red meat
        rather than poultry, the whole butchery-and-charcuterie repertoire opens.
      </p>
      {redMeat.map((f) => (
        <FrameCard key={f.name} card={f} active={form?.name === f.name} onCommit={commitForm} />
      ))}
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
