import { useEffect, useRef } from 'react'
import markup from './markup.html?raw'
import { init } from './culinai.js'

/**
 * Thin React shell around the original CulinAI workspace.
 *
 * The app is (for now) imperative DOM code driven by `render()` and inline
 * `onclick` handlers, so we inject the original markup verbatim and let the
 * logic module take over once it's mounted. `culinai.js` exposes its handlers
 * on `window` (so the inline attributes resolve) and exports `init()`, which we
 * call in an effect — after the markup is committed to the DOM.
 *
 * Future work: replace `dangerouslySetInnerHTML` + `init()` with real
 * components and React state, one lens/pane at a time.
 */
export default function App() {
  const ref = useRef(null)

  useEffect(() => {
    init()
  }, [])

  return <div ref={ref} dangerouslySetInnerHTML={{ __html: markup }} />
}
