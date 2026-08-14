import { useWorkspace } from '../context/WorkspaceContext.jsx'
import { useAssociation } from '../lib/useAssociation.js'
import { LENSES, LENS_KEYS, LENS_LABELS } from '../lib/associationEngine.js'
import Chip from './Chip.jsx'

const LENS_CLASS = {
  compound: 'l-c',
  tradition: 'l-t',
  'co-occurrence': 'l-o',
}

const SINGLE_CAP = 14

function LensTags({ lenses }) {
  return (
    <span className="assoc-lenses">
      {lenses.map((l) => (
        <span key={l} className={`assoc-l ${LENS_CLASS[l]}`}>
          {LENS_LABELS[l]}
        </span>
      ))}
    </span>
  )
}

export default function AssociationPanel() {
  const { dish, form, cuisineScope } = useWorkspace()
  const { loading, data, error } = useAssociation(dish, form, cuisineScope)

  if (error) {
    return (
      <section className="pane pane-a on">
        <div className="notice err">
          <strong>Association engine failed.</strong> {error.message || String(error)}
        </div>
      </section>
    )
  }

  if (!data) {
    return (
      <section className="pane pane-a on">
        <div className="notice">Asking every lens…</div>
      </section>
    )
  }

  const convergent = data.combined.filter((c) => c.agreement === 'multi')
  const corpusDown = data.cooccur.status === 'error'

  return (
    <section className="pane pane-a on">
      <div className={`notice ${corpusDown ? 'err' : 'ok'}`}>
        {corpusDown ? (
          <>
            <strong>Two lenses answering.</strong> Chemistry and tradition merged; the corpus
            lens is unreachable — {data.cooccur.error}
          </>
        ) : (
          <>
            <strong>Three lenses answering.</strong> Chemistry, tradition and the corpus around{' '}
            <em>{data.seed}</em>
            {loading ? ' · refreshing…' : ''}
          </>
        )}
      </div>

      <p className="pane-intro">
        Here is what chemistry, tradition and the corpus each suggest for this set — and where
        they agree or pull apart. Nothing here is ranked against anything else, and nothing is
        added to the dish until you click it.
      </p>

      {data.form && (
        <div className="assoc-ctx">
          <span className="ac-lbl">Form context</span>
          Locked form <em>{data.form.name}</em>. It is not a source of suggestions — it decides
          what the ones below can actually do.
        </div>
      )}

      <div className="group">
        <div className="g-label">
          Where the lenses converge
          <span className="posture p-est">{convergent.length} agreed</span>
        </div>
        <div className="g-why">
          Named independently by two or more lenses. That is a count of how many ways of looking
          arrived at the same ingredient — not a score, and not a recommendation.
        </div>
        {convergent.length ? (
          <div className="assoc-grid">
            {convergent.map((c) => (
              <div key={c.name} className={`assoc-hit${c.engaged ? ' engaged' : ''}`}>
                <Chip name={c.name} lens={c.primaryLens} />
                <LensTags lenses={c.lenses} />
                <div className="assoc-why">{c.reasons.slice(0, 2).join(' · ')}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="no-modes">
            No ingredient was named by more than one lens. They are describing this set in
            genuinely different terms — see below.
          </div>
        )}
      </div>

      {!!data.disagreements.length && (
        <div className="group">
          <div className="g-label">
            Where they pull apart
            <span className="posture p-inf">flagged · not resolved</span>
          </div>
          <div className="g-why">
            Nothing is hidden because another lens disagreed. These are different frames on the
            same plate, and picking between them is your call.
          </div>
          {data.disagreements.map((d, i) => (
            <div className="assoc-dis" key={`${d.theme}-${i}`}>
              <div className="ad-theme">
                {d.theme}
                <LensTags lenses={d.lenses} />
              </div>
              <p className="ad-sum">{d.summary}</p>
              {d.candidates
                .filter((c) => c.names.length)
                .map((c, ci) => (
                  <div className="ad-row" key={ci}>
                    <span className="ad-lens">{c.note || LENS_LABELS[c.lens]}</span>
                    <span className="ad-names">{c.names.join(', ')}</span>
                  </div>
                ))}
            </div>
          ))}
        </div>
      )}

      {LENSES.map((lens) => {
        const singles = data.combined.filter(
          (c) => c.agreement === 'single' && c.primaryLens === lens
        )
        if (!singles.length) return null
        const shown = singles.slice(0, SINGLE_CAP)
        return (
          <div className="group" key={lens}>
            <div className="g-label">
              {LENS_LABELS[lens]} alone
              <span className={`posture ${lens === 'co-occurrence' ? 'p-corp' : 'p-doc'}`}>
                {singles.length}
              </span>
            </div>
            <div className="g-why">
              Only this lens named these. Single-lens is not weaker evidence — it usually means
              the others were answering a different question.
            </div>
            <div className="chips">
              {shown.map((c) => (
                <Chip key={c.name} name={c.name} lens={lens} />
              ))}
            </div>
            {singles.length > shown.length && (
              <div className="assoc-more">
                {singles.length - shown.length} more in the {LENS_LABELS[lens]} tab.
              </div>
            )}
          </div>
        )
      })}

      <div className="closer">
        Every lens tab still stands on its own. This view merges them; it does not replace them,
        and it keeps no memory of what you do here.
      </div>
    </section>
  )
}
