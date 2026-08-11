import { TRADITION_GROUPS } from '../data/tradition.js'
import { useWorkspace } from '../context/WorkspaceContext.jsx'
import ChipGroup from './ChipGroup.jsx'

export default function TraditionPane() {
  const { cuisineScope, overlayNote, form } = useWorkspace()
  return (
    <section className="pane pane-t on">
      <p className="pane-intro">
        Across documented duck threads, the first question is often not <em>what goes with
        duck</em> but <em>what state of duck are you designing?</em> Each thread below is
        named — never a whole cuisine.
      </p>
      {cuisineScope && (
        <div className="scope-lens-note">
          <span className="sn-lbl">Cuisine scope · {cuisineScope.label}</span>
          Threads in scope are marked. Nothing is hidden — flag, never filter.
        </div>
      )}
      {form && overlayNote && (
        <div className="overlay-note">
          <span className="on-lbl">Form overlay · {form.name}</span>
          {overlayNote}
        </div>
      )}
      {TRADITION_GROUPS.map((g, i) => (
        <ChipGroup key={g.title} group={g} id={`t-${i}`} showRegion />
      ))}
      <div className="closer">
        This still isn&apos;t a closed list. These are what&apos;s documented, not what&apos;s
        permitted.
      </div>
    </section>
  )
}
