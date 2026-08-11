import { useWorkspace } from '../context/WorkspaceContext.jsx'
import Chip from './Chip.jsx'

export default function ChipGroup({ group, id, showRegion = false }) {
  const { cuisineScope, openWhy, toggleWhy, tensionFor } = useWorkspace()
  const whyId = id || `why-${group.title}`
  const open = openWhy.has(whyId)

  let regionClass = ''
  let regionFlag = null
  if (showRegion && group.region) {
    const keys = group.region.split(',')
    if (cuisineScope) {
      const match = keys.some((k) => cuisineScope.keys.includes(k))
      regionClass = match ? 'region-match' : 'region-nomatch'
      regionFlag = match ? (
        <span className="region-flag match">in scope</span>
      ) : (
        <span className="region-flag nomatch">outside scope</span>
      )
    }
  }

  const requires = group.whyBox?.requires
  const tension = requires ? tensionFor(requires) : null

  return (
    <div className={`group ${regionClass}`.trim()}>
      <div className="g-label">
        {group.title}
        {group.thread && <span className="g-thread">{group.thread}</span>}
        {group.posture && (
          <span className={`posture ${group.postureClass || 'p-doc'}`}>{group.posture}</span>
        )}
        {regionFlag}
      </div>
      {group.why && <div className="g-why">{group.why}</div>}
      <div className="chips">
        {group.chips.map((name) => (
          <Chip key={name} name={name} lens={group.lens} />
        ))}
      </div>
      {group.extend && (
        <div className="extend">
          <span className="x-lbl">
            Extends the principle · not in this thread{' '}
            <span className="posture p-inf" style={{ marginLeft: '.3rem' }}>
              inferred · CulinAI
            </span>
          </span>
          <p className="x-why">{group.extend.why}</p>
          <div className="chips">
            {group.extend.chips.map((name) => (
              <Chip key={name} name={name} lens={group.lens} className="xchip" />
            ))}
          </div>
        </div>
      )}
      {group.whyBox && (
        <>
          <button className="deeper" type="button" onClick={() => toggleWhy(whyId)}>
            {open ? (group.lens === 'compound' ? 'Why these ↑' : 'What transfers ↑') : (group.lens === 'compound' ? 'Why these →' : 'What transfers →')}
          </button>
          {open && (
            <div className="why-box open">
              {group.whyBox.sections.map((s, i) => (
                <div key={i}>
                  <div className="why-lbl">{s.label}</div>
                  <p className={s.className || undefined}>{s.text}</p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
      {tension && (
        <div className="tension">
          <span className="t-lbl">Tension with form</span>
          <p>
            Locked form <em>{tension.form}</em> does not produce: {tension.missing.join(', ')}.
          </p>
          <div className="t-q">Keep the form, adapt the thread — or change the form?</div>
        </div>
      )}
    </div>
  )
}
