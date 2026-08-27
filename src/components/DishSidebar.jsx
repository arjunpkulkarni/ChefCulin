import { useWorkspace } from '../context/WorkspaceContext.jsx'
import { COLORS } from '../data/domain.js'
import { AXIS_LABELS, BALANCE_DECISIONS } from '../lib/balance.js'

const DECISION_LABELS = { accept: 'Accept', adjust: 'Adjust', override: 'Override' }

export default function DishSidebar() {
  const {
    dish,
    form,
    focusIngredient,
    phase,
    balance,
    balanceDecisionFor,
    recordBalanceDecision,
    balanceDecisions,
    saveDish,
    discardDish,
    saveState,
    savedNow,
    discardedNow,
    kept,
    clearForm,
    openIdx,
    openModes,
    setMode,
    duplicateIn,
    removeAt,
    modesFor,
  } = useWorkspace()

  const formed = dish.filter((d) => d.mode).length
  const trend = balance.primaryTrend
  const decided = balanceDecisionFor(trend)
  const saving = saveState.status === 'saving'

  return (
    <aside className="dish">
      <div className="dish-eyebrow">The dish</div>
      <div className="dish-title">Untitled — {focusIngredient}</div>

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
              className={`axis${balance.flaggedAxes.includes(key) ? ' flagged' : ''}`}
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

        {/* E4 — the flag and its corrective pair. Nothing is added to the dish
            here: the suggestion names an axis, the chef picks the ingredient. */}
        {trend && (
          <div className="trend" data-axis={trend.axis}>
            <div className="trend-head">
              <span className="trend-ax">
                {AXIS_LABELS[trend.axis]} <span className="trend-arrow">→</span> {trend.pair}
              </span>
              <span className="trend-share">{Math.round(trend.share * 100)}%</span>
            </div>
            <div className="trend-sug">{trend.suggestion}</div>
            <div className="trend-note">{trend.note}</div>
            {decided ? (
              <div className="trend-logged">
                Logged <strong>{decided.decision}</strong> — session only, nothing saved.
              </div>
            ) : (
              <div className="trend-acts">
                {BALANCE_DECISIONS.map((d) => (
                  <button
                    key={d}
                    type="button"
                    className={`trend-b ${d}`}
                    onClick={() => recordBalanceDecision(d, trend)}
                  >
                    {DECISION_LABELS[d]}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {balance.msg && <div className={balance.msgClass}>{balance.msg}</div>}
      </div>

      {/* F6 — the only write in this app. Save commits a snapshot to Palate
          Memory; Discard is an explicit no-op, exactly like PalateStore.discard(). */}
      <div className="dish-sec f6">
        <h4>
          <span>Keep this dish</span>
          {!!kept.rows.length && <span>{kept.rows.length} kept</span>}
        </h4>

        {!dish.length ? (
          <div className="dish-empty">Nothing to keep yet.</div>
        ) : (
          <>
            <div className="f6-acts">
              <button
                type="button"
                className="f6-b save"
                onClick={saveDish}
                disabled={saving || savedNow}
              >
                {saving ? 'Saving…' : savedNow ? 'Saved' : 'Save'}
              </button>
              <button
                type="button"
                className="f6-b discard"
                onClick={discardDish}
                disabled={saving || discardedNow}
              >
                {discardedNow ? 'Discarded' : 'Discard'}
              </button>
            </div>

            {savedNow && (
              <div className="f6-note ok">
                Kept in Palate Memory. Change anything above and it becomes a new dish to keep.
              </div>
            )}
            {discardedNow && (
              <div className="f6-note">
                Discarded — nothing was written. Discard is a no-op by design, not a delete.
              </div>
            )}
            {saveState.status === 'error' && saveState.error && (
              <div className="f6-note err">
                Not saved. {saveState.error}
                <span className="f6-hint">
                  Palate Memory needs Postgres: cd pipeline &amp;&amp; docker compose up -d
                </span>
              </div>
            )}
            {!savedNow && !discardedNow && saveState.status !== 'error' && (
              <div className="f6-note">
                Saving keeps the ingredients, their forms, the frame and the scope — nothing
                else.
                {balanceDecisions.length > 0 && (
                  <span className="f6-hint">
                    {balanceDecisions.length} balance decision
                    {balanceDecisions.length > 1 ? 's' : ''} this session stay in the session.
                  </span>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </aside>
  )
}
