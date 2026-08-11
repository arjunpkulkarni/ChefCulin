import { useWorkspace } from '../context/WorkspaceContext.jsx'
import { DELIVERY } from '../data/domain.js'

export default function Chip({ name, lens, meta, className = '' }) {
  const { dish, addIngredient, colors } = useWorkspace()
  const added = dish.some((d) => d.name === name)
  const formDependent = Object.prototype.hasOwnProperty.call(DELIVERY, name)
  return (
    <span
      className={`chip${added ? ' added' : ''}${formDependent ? ' form-dependent' : ''}${className ? ' ' + className : ''}`}
      style={{ '--ac': colors[lens] || 'var(--plum)' }}
      data-name={name}
      title={
        formDependent
          ? 'Function depends on how you use it — see Delivery modes once added.'
          : undefined
      }
      onClick={() => addIngredient(name, lens)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') addIngredient(name, lens)
      }}
    >
      <span className="plus">{added ? '✓' : '+'}</span>
      {name}
      {meta != null && <span className="chip-meta">{meta}</span>}
    </span>
  )
}
