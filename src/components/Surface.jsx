import { useWorkspace } from '../context/WorkspaceContext.jsx'
import CompoundPane from './CompoundPane.jsx'
import TraditionPane from './TraditionPane.jsx'
import CooccurPane from './CooccurPane.jsx'
import AssociationPanel from './AssociationPanel.jsx'
import FormPane from './FormPane.jsx'
import BrainstormPane from './BrainstormPane.jsx'

/* Associate sits after the three lenses it merges. It is an additional view,
   not a replacement — every lens tab still stands on its own. */
const TABS = [
  { k: 'c', label: 'Compound', className: 'tab-c' },
  { k: 't', label: 'Tradition', className: 'tab-t' },
  { k: 'o', label: 'Co-occurrence', className: 'tab-o' },
  { k: 'a', label: 'Associate', className: 'tab-a' },
  { k: 'f', label: 'Form', className: 'tab-f' },
  { k: 'b', label: 'Brainstorm', className: 'tab-b' },
]

export default function Surface() {
  const { activeLens, setActiveLens, chat, focusIngredient } = useWorkspace()

  return (
    <main className="surface">
      <div className="chefline">Designing a dish around {focusIngredient}.</div>
      <div className="lens-tabs">
        {TABS.map((t) => (
          <button
            key={t.k}
            type="button"
            className={`tab ${t.className}${activeLens === t.k ? ' on' : ''}`}
            onClick={() => setActiveLens(t.k)}
          >
            <span className="dot" />
            {t.label}
            {t.k === 'b' && chat.length > 0 && (
              <span className="tab-badge">{chat.length}</span>
            )}
          </button>
        ))}
      </div>
      {activeLens === 'c' && <CompoundPane />}
      {activeLens === 't' && <TraditionPane />}
      {activeLens === 'o' && <CooccurPane />}
      {activeLens === 'a' && <AssociationPanel />}
      {activeLens === 'f' && <FormPane />}
      {activeLens === 'b' && <BrainstormPane />}
    </main>
  )
}
