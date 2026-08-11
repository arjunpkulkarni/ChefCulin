import { COMPOUND_GROUPS } from '../data/compound.js'
import { useWorkspace } from '../context/WorkspaceContext.jsx'
import ChipGroup from './ChipGroup.jsx'

export default function CompoundPane() {
  const { cuisineScope, overlayNote, form } = useWorkspace()
  return (
    <section className="pane pane-c on">
      <p className="pane-intro">
        Grouped by the sensory job each ingredient does around duck&apos;s fat and browned
        surface. Nothing here is ranked — pick what interests you.
      </p>
      {cuisineScope && (
        <div className="scope-lens-note">
          <span className="sn-lbl">Cuisine scope locked · {cuisineScope.label}</span>
          This lens computes exactly the same with or without a locked scope — chemistry
          isn&apos;t regional. Tradition is where scope flags apply.
        </div>
      )}
      {form && overlayNote && (
        <div className="overlay-note">
          <span className="on-lbl">Form overlay · {form.name}</span>
          {overlayNote}
          <span className="on-foot">Applies across lenses — delivery and placement shift with form.</span>
        </div>
      )}
      {COMPOUND_GROUPS.map((g, i) => (
        <ChipGroup key={g.title} group={g} id={`c-${i}`} />
      ))}
      <div className="closer">
        Add what interests you — or move to another lens. Nothing commits you to a direction.
      </div>
    </section>
  )
}
