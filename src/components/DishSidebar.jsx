import { useWorkspace } from '../context/WorkspaceContext.jsx'
import { COLORS } from '../data/domain.js'

export default function DishSidebar() {
  const {
    dish,
    form,
    phase,
    balance,
    clearForm,
    openIdx,
    openModes,
    setMode,
    duplicateIn,
    removeAt,
    modesFor,
  } = useWorkspace()

  const formed = dish.filter((d) => d.mode).length

  return (
    <aside className="dish">
      <div className="dish-eyebrow">The dish</div>
      <div className="dish-title">Untitled — duck breast</div>

      <div className={phase.className}>
        <span className="ph-l">{phase.label}</span>
        {phase.text}
      </div>

      {form && (
        <div className="dish-sec">
          <h4>
            <span>Form</span>
            <button type="button" className="clearf" onClick={clearForm}>
              clear
            </button>
          </h4>
          <div className="fcard">
            <div className="fn">{form.name}</div>
            <div className="fd">{form.desc}</div>
          </div>
        </div>
      )}

      <div className="dish-sec">
        <h4>
          <span>Committed</span>
          <span>
            {formed}/{dish.length}
          </span>
        </h4>
        <div>
          {!dish.length ? (
            <div className="dish-empty">
              Nothing gathered yet. Add ingredients from the right — then give each one a form.
            </div>
          ) : (
            dish.map((d, i) => {
              const modes = modesFor(d.name)
              const unformed = !d.mode
              return (
                <div
                  key={`${d.name}-${i}`}
                  className={`ing${unformed ? ' unformed' : ''}`}
                  style={{ '--src': COLORS[d.lens] || 'var(--skin)' }}
                >
                  <div className="ing-top">
                    <span className="ing-n">{d.name}</span>
                    <span className="ing-m">{d.mode || 'no form yet'}</span>
                    <div className="ing-btns">
                      <button type="button" className="mini" onClick={() => openModes(i)}>
                        {modes ? 'form' : '—'}
                      </button>
                      {d.mode && modes && (
                        <button type="button" className="mini" onClick={() => duplicateIn(i)}>
                          +mode
                        </button>
                      )}
                      <button type="button" className="mini x" onClick={() => removeAt(i)}>
                        ×
                      </button>
                    </div>
                  </div>
                  {d.modeNote && <div className="ing-note">{d.modeNote}</div>}
                  {openIdx === i && (
                    <div className="modes">
                      {!modes ? (
                        <div className="no-modes">
                          No delivery modes on file for this ingredient yet.
                        </div>
                      ) : (
                        modes.map((m, mi) => (
                          <button
                            key={m.mode}
                            type="button"
                            className="mode-b"
                            onClick={() => setMode(i, mi)}
                          >
                            <span className="mode-n">{m.mode}</span>
                            <span className="mode-w">{m.note}</span>
                          </button>
                        ))
                      )}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>

      <div className="dish-sec">
        <h4>Balance read</h4>
        <div className="balance">
          {[
            ['umami', balance.umamiLabel, balance.umamiResolved],
            ['salt', 'Salt', false],
            ['fat', 'Fat', false],
            ['acid', 'Acid', false],
            ['sweet', 'Sweet', false],
            ['heat', balance.heatLabel, balance.heatResolved],
          ].map(([key, label, resolved]) => (
            <div
              key={key}
              className={`axis${balance.flagged === key ? ' flagged' : ''}`}
              data-axis={key}
            >
              <span className={`an${resolved ? ' resolved' : ''}`}>{label}</span>
              <div className="bar">
                <div className="fill" style={{ width: `${balance.widths[key]}%` }} />
                {key === 'umami' && balance.synGhost && (
                  <div
                    className="synergy show"
                    style={{
                      left: `${balance.synGhost.left}%`,
                      width: `${balance.synGhost.width}%`,
                    }}
                  />
                )}
              </div>
            </div>
          ))}
        </div>
        <div className={balance.msgClass}>{balance.msg}</div>
      </div>
    </aside>
  )
}
