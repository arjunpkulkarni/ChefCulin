import { useEffect, useState } from 'react'
import { associate } from './associationEngine.js'

/**
 * Runs the Association Engine whenever the dish, form or cuisine scope changes.
 *
 * Debounced, because adding three chips in a row should ask the corpus once.
 * Cancels in flight so a slow response for an old dish cannot overwrite a fast
 * one for the current dish.
 */
export function useAssociation(dish, form, cuisineScope, options = {}) {
  const { debounceMs = 120, api } = options
  const [state, setState] = useState({ loading: true, data: null, error: null })

  useEffect(() => {
    let cancelled = false
    setState((s) => ({ ...s, loading: true }))
    const timer = setTimeout(() => {
      associate({ dish, form, cuisineScope }, { api })
        .then((data) => {
          if (!cancelled) setState({ loading: false, data, error: null })
        })
        .catch((err) => {
          if (!cancelled) setState({ loading: false, data: null, error: err })
        })
    }, debounceMs)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [dish, form, cuisineScope, debounceMs, api])

  return state
}
