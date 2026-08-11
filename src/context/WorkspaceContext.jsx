import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { COLORS, FRAMES, OVERLAYS, PROP_LABELS, modesFor } from '../data/domain.js'
import { computeBalance, phaseOf } from '../lib/balance.js'
import {
  buildWriteUp,
  directions,
  matchFrame,
  matchRegion,
  observations,
} from '../lib/chat.js'
import { REGION_PICKS } from '../data/domain.js'

const WorkspaceContext = createContext(null)

export function WorkspaceProvider({ children }) {
  const [dish, setDish] = useState([])
  const [form, setForm] = useState(null)
  const [cuisineScope, setCuisineScope] = useState(null)
  const [activeLens, setActiveLens] = useState('c')
  const [openIdx, setOpenIdx] = useState(null)
  const [openWhy, setOpenWhy] = useState(() => new Set())
  const [scopeMenuOpen, setScopeMenuOpen] = useState(false)
  const [chat, setChat] = useState([])

  const balance = useMemo(() => computeBalance(dish, form), [dish, form])
  const phase = useMemo(() => phaseOf(dish), [dish])

  const push = useCallback((who, content) => {
    setChat((c) => [...c, { who, content }])
  }, [])

  const addIngredient = useCallback((name, lens) => {
    setDish((d) => {
      if (d.find((x) => x.name === name)) return d
      return [...d, { name, lens, mode: null, modeNote: null, axAdd: null }]
    })
  }, [])

  const removeIngredient = useCallback((name) => {
    setDish((d) => d.filter((x) => x.name !== name))
    setOpenIdx(null)
  }, [])

  const removeAt = useCallback((i) => {
    setDish((d) => {
      const next = d.slice()
      next.splice(i, 1)
      return next
    })
    setOpenIdx(null)
  }, [])

  const openModes = useCallback((i) => {
    setOpenIdx((cur) => (cur === i ? null : i))
  }, [])

  const setMode = useCallback((i, mi) => {
    setDish((d) => {
      const next = d.slice()
      const item = { ...next[i] }
      const modes = modesFor(item.name)
      if (!modes) return d
      const m = modes[mi]
      item.mode = m.mode
      item.modeNote = m.note
      item.axAdd = m.axAdd
      next[i] = item
      return next
    })
    setOpenIdx(null)
  }, [])

  const duplicateInFixed = useCallback((i) => {
    setDish((d) => {
      const src = d[i]
      const next = [
        ...d,
        { name: src.name, lens: src.lens, mode: null, modeNote: null, axAdd: null },
      ]
      setOpenIdx(next.length - 1)
      return next
    })
  }, [])

  const commitForm = useCallback((name, desc) => {
    setForm((f) => (f && f.name === name ? null : { name, desc }))
  }, [])

  const clearForm = useCallback(() => setForm(null), [])

  const lockCuisine = useCallback((key, label) => {
    const keys = key.split(',')
    setCuisineScope((cur) => {
      if (cur && cur.keys.join(',') === keys.join(',')) return null
      return { label, keys }
    })
    setScopeMenuOpen(false)
  }, [])

  const clearCuisine = useCallback(() => {
    setCuisineScope(null)
    setScopeMenuOpen(false)
  }, [])

  const lockCuisineFromInput = useCallback(
    (raw) => {
      const text = raw.trim()
      if (!text) return
      setScopeMenuOpen(false)
      const match = matchRegion(text)
      if (match) lockCuisine(match.keys.join(','), match.label)
      else {
        setActiveLens('b')
        push('me', { type: 'text', text: `Cuisine scope: ${text}` })
        const known = REGION_PICKS.map((p) => p.label).join(', ')
        push('sys', {
          type: 'blocks',
          blocks: [
            {
              type: 'p',
              html: false,
              text: `No documented thread exists yet for ${text} — locking it would show you an empty result, or worse, a guessed one, and neither is honest.`,
            },
            {
              type: 'p',
              text: `What's actually documented right now: ${known}. If ${text} is close to one of these, say which — otherwise this stays open until a real thread is authored.`,
            },
            {
              type: 'ask',
              text: 'Lock one of the documented regions instead, or keep browsing without a scope?',
            },
          ],
        })
      }
    },
    [lockCuisine, push]
  )

  const toggleWhy = useCallback((id) => {
    setOpenWhy((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const respond = useCallback(
    (qRaw) => {
      const q = qRaw.toLowerCase()
      const scopeCmd = q.match(/^(?:lock|cuisine scope|scope)\s*(?:to|:)?\s+(.+)/)
      if (scopeCmd) {
        const raw = scopeCmd[1].trim()
        const match = matchRegion(raw)
        if (match) {
          lockCuisine(match.keys.join(','), match.label)
          push('sys', {
            type: 'blocks',
            blocks: [
              {
                type: 'p',
                text: `Locked to ${match.label}. Tradition threads are flagged accordingly — nothing is hidden, and compound and co-occurrence stay fully unfiltered.`,
              },
            ],
          })
        } else {
          lockCuisineFromInput(raw)
        }
        return
      }

      const frameMatch = matchFrame(q)
      if (frameMatch && dish.length === 0) {
        const desc = FRAMES[frameMatch]
          ? Object.entries(PROP_LABELS)
              .filter(([k]) => FRAMES[frameMatch].produces.includes(k))
              .map(([, v]) => v)
              .slice(0, 2)
              .join('; ')
          : ''
        commitForm(frameMatch, desc || frameMatch)
        push('sys', {
          type: 'blocks',
          blocks: [
            {
              type: 'p',
              text: `Set the form to ${frameMatch} — you can see it under the Form tab, and change your mind any time by clicking it again. Ingredients still gather however you like; this just answers "what state of duck," not "what's in it."`,
            },
          ],
        })
        return
      }

      if (dish.length === 0) {
        push('sys', {
          type: 'blocks',
          blocks: [
            {
              type: 'p',
              text: "Nothing gathered yet — and I won't pick for you. Choosing the ingredients is the creative act, and it's yours. Work through the lenses, pull what interests you, and then we can talk about what to do with it.",
            },
          ],
        })
        return
      }

      if (/suggest|direction|idea|what could|options|not sure|help me/.test(q)) {
        const D = directions(dish)
        if (!D) {
          push('sys', {
            type: 'blocks',
            blocks: [
              {
                type: 'p',
                text: `You have ${dish.length} ingredient${dish.length > 1 ? 's' : ''}. That's not really a set yet — anything I suggested would be me designing the dish, not arranging yours.`,
              },
              { type: 'p', text: 'Pull a few more and the arrangement question gets real.' },
            ],
          })
          return
        }
        push('sys', {
          type: 'blocks',
          blocks: [
            {
              type: 'p',
              text: `Here are ${D.length} directions. They are genuinely different dishes, not variations — and I'm not ranking them.`,
            },
            ...D.map((d) => ({ type: 'dir', ...d })),
            { type: 'ask', text: "Which of these is closest to what you're seeing?" },
          ],
        })
        return
      }

      if (/missing|lacking|need|gap|absent/.test(q)) {
        const o = observations(dish).filter((x) =>
          /Nothing here catches|There is no reset|No textural/.test(x)
        )
        if (!o.length) {
          push('sys', {
            type: 'blocks',
            blocks: [
              {
                type: 'p',
                text: "Nothing structural is missing — you have savoury depth, a reset, and a carrier. What's left is arrangement, not addition.",
              },
            ],
          })
          return
        }
        push('sys', {
          type: 'blocks',
          blocks: [
            ...o.map((t) => ({ type: 'p', text: t })),
            { type: 'ask', text: 'None of these is a problem unless you think it is.' },
          ],
        })
        return
      }

      if (/write|recipe|outline|summar|describe|done|finish/.test(q)) {
        push('sys', { type: 'writeup', ...buildWriteUp(dish, form) })
        return
      }

      const o = observations(dish)
      if (!o.length) {
        push('sys', {
          type: 'blocks',
          blocks: [
            {
              type: 'p',
              text: "Nothing is jumping out. Tell me what you're trying to make it feel like and I'll tell you what's in the way.",
            },
          ],
        })
        return
      }
      push('sys', {
        type: 'blocks',
        blocks: [
          ...o.slice(0, 3).map((t) => ({ type: 'p', text: t })),
          {
            type: 'ask',
            text: 'Any of that useful, or are you working toward something specific?',
          },
        ],
      })
    },
    [commitForm, dish, form, lockCuisine, lockCuisineFromInput, push]
  )

  const sendChat = useCallback(
    (txt) => {
      const text = (txt || '').trim()
      if (!text) return
      push('me', { type: 'text', text })
      setTimeout(() => respond(text), 320)
    },
    [push, respond]
  )

  const tensionFor = useCallback(
    (requires) => {
      if (!form || !FRAMES[form.name] || !requires?.length) return null
      const absent = new Set(FRAMES[form.name].absent || [])
      const hits = requires.filter((r) => absent.has(r))
      if (!hits.length) return null
      return {
        form: form.name,
        missing: hits.map((h) => PROP_LABELS[h] || h),
      }
    },
    [form]
  )

  const overlayNote = useMemo(() => {
    if (!form || !FRAMES[form.name]) return null
    const key = FRAMES[form.name].overlay
    return OVERLAYS[key] || null
  }, [form])

  const value = {
    dish,
    form,
    cuisineScope,
    activeLens,
    setActiveLens,
    openIdx,
    openWhy,
    scopeMenuOpen,
    setScopeMenuOpen,
    chat,
    balance,
    phase,
    colors: COLORS,
    regionPicks: REGION_PICKS,
    addIngredient,
    removeIngredient,
    removeAt,
    openModes,
    setMode,
    duplicateIn: duplicateInFixed,
    commitForm,
    clearForm,
    lockCuisine,
    clearCuisine,
    lockCuisineFromInput,
    toggleWhy,
    sendChat,
    tensionFor,
    overlayNote,
    modesFor,
  }

  return (
    <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
  )
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext)
  if (!ctx) throw new Error('useWorkspace outside provider')
  return ctx
}
