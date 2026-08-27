/**
 * Shared option card for agent panels (Tradition first).
 * Provenance stamp uses confidence / documentation fields when present.
 */
export default function OptionCard({
  option,
  selected = false,
  onSelect,
  stamp = null,
  disabled = false,
}) {
  return (
    <button
      type="button"
      className={`option-card${selected ? ' selected' : ''}`}
      onClick={() => onSelect?.(option)}
      disabled={disabled}
    >
      <div className="option-card-top">
        <span className="option-card-title">{option.title}</span>
        {typeof option.score === 'number' && option.score > 0 && (
          <span className="option-card-score">{option.score}</span>
        )}
      </div>
      {option.subtitle && <div className="option-card-sub">{option.subtitle}</div>}
      {stamp && (
        <div className="option-stamp" title={stamp.title || ''}>
          {stamp.label}
        </div>
      )}
    </button>
  )
}
