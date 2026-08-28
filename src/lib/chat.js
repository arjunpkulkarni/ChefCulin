import {
  AXES,
  AXADD_JOB,
  FRAME_ALIASES,
  FRAMES,
  FUNCTION_OF,
  ING_CLASS,
  REGION_ALIASES,
  REGION_PICKS,
  anchorFor,
  axesFor,
} from '../data/domain.js'

export function matchRegion(raw) {
  const r = raw.toLowerCase().trim()
  const direct = REGION_PICKS.find(
    (p) => p.label.toLowerCase() === r || p.key.split(',').includes(r)
  )
  if (direct) return { keys: direct.key.split(','), label: direct.label }
  const alias = REGION_ALIASES[r]
  if (alias) {
    const p = REGION_PICKS.find(
      (x) => x.key === alias || x.key.split(',').includes(alias.split(',')[0])
    )
    if (p) return { keys: p.key.split(','), label: p.label }
  }
  return null
}

export function matchFrame(q) {
  const lower = q.toLowerCase()
  for (const [alias, name] of Object.entries(FRAME_ALIASES)) {
    if (lower.includes(alias)) return name
  }
  for (const name of Object.keys(FRAMES)) {
    if (lower.includes(name.toLowerCase())) return name
  }
  return null
}

function dishRead(dish, anchor = anchorFor(null)) {
  const hasFocus = Boolean(anchor?.name)
  const t = {
    glut: hasFocus ? (anchor.glut ?? 0) : 0,
    nucl: hasFocus ? (anchor.nucl ?? 0) : 0,
    salt: 0,
    fat: hasFocus ? (anchor.fat ?? 0) : 0,
    acid: 0,
    sweet: 0,
    capsaicin: 0,
    pungent: 0,
    trigeminal: 0,
  }
  dish.forEach((d) => {
    const b = axesFor(d.name)
    for (const k in b) if (k in t) t[k] += b[k]
    const a = d.axAdd || {}
    for (const k in a) if (k in t) t[k] += a[k]
  })
  const jobs = {}
  const addJob = (f, name) => {
    if (!f) return
    ;(jobs[f] = jobs[f] || []).push(name)
  }
  dish.forEach((d) => {
    const staticJob = FUNCTION_OF[ING_CLASS[d.name] || ING_CLASS[d.name?.toLowerCase?.()]] || 'other'
    addJob(staticJob, d.name)
    const add = d.axAdd || {}
    Object.keys(add).forEach((axis) => {
      const derivedJob = AXADD_JOB[axis]
      if (
        derivedJob &&
        derivedJob !== staticJob &&
        !(jobs[derivedJob] || []).includes(d.name)
      ) {
        addJob(derivedJob, d.name)
      }
    })
  })
  return { t, jobs }
}

export function observations(dish, anchor = anchorFor(null)) {
  const { t, jobs } = dishRead(dish, anchor)
  const o = []
  const names = dish.map((d) => d.name)
  const focus = anchor.name || 'the focus ingredient'

  if (t.glut > (anchor.glut ?? 0) && t.nucl > (anchor.nucl ?? 0))
    o.push(
      `You have glutamate and nucleotide sources both in play, and ${focus} brings a nucleotide baseline. The savoury depth here is multiplying, not adding — that is a big lever, and it is already pulled.`
    )
  else if (t.glut > (anchor.glut ?? 0) && t.nucl === (anchor.nucl ?? 0))
    o.push(
      `${focus} already carries a nucleotide baseline, so the glutamate you have added is amplifying rather than accumulating. A dried mushroom or an aged cheese would push that further — but you may already be where you want to be.`
    )

  if (!jobs['a carrier for the fat'])
    o.push(
      'Nothing here catches rendered fat or richness. That is a real choice, not an omission — but it is worth making on purpose. A starch, a bread, a bean, a purée.'
    )
  if (!jobs.acid && !jobs['acid and sweetness'] && !jobs['acid and body'])
    o.push(
      `There is no reset. ${focus} can read rich and accumulative — something sour, tart, or drying gives the palate somewhere to go between bites.`
    )
  if (!jobs['freshness and crunch'])
    o.push(
      'No textural contrast. Everything here is soft or rendered. Worth asking whether you want something raw against it.'
    )

  const aromatics = (jobs['aromatic lift'] || []).length
  if (aromatics >= 3)
    o.push(
      `You have ${aromatics} aromatics — ${(jobs['aromatic lift'] || []).join(', ')}. They are competing for the same channel rather than layering. That can be deliberate, but three is a lot of voices in one register.`
    )

  if (t.capsaicin > 0 && t.acid === 0 && !names.includes('coconut milk'))
    o.push(
      'There is heat with nothing fat or sweet to carry it. Capsaicin is lipophilic — it needs fat to spread, or it just sits and burns in one place.'
    )

  const unformed = dish.filter((d) => !d.mode)
  if (unformed.length && dish.length > 2)
    o.push(
      `Still undecided: ${unformed.map((d) => d.name).join(', ')}. Where each one sits will change the dish more than which one it is.`
    )

  return o
}

export function directions(dish, anchor = anchorFor(null)) {
  if (dish.length < 3) return null
  const { jobs } = dishRead(dish, anchor)
  const names = dish.map((d) => d.name)
  const has = (n) => names.includes(n)
  const focus = anchor.name || 'the focus ingredient'
  const D = [
    {
      t: `${focus} stays the plate`,
      b: 'The centrepiece stays intact — seared, roasted, or sliced as your form dictates. Supporting ingredients sit beside it as discrete elements rather than dissolving into a sauce. The tension is between the main register and whatever is sharp on the plate.',
      w: 'This asks the least of the other ingredients and the most of your cooking. The centrepiece has nowhere to hide.',
    },
    {
      t: `${focus} disappears into a system`,
      b:
        'Broth, braise, or sauce. Richness leaves the plate and becomes structure — everything gathered goes into a liquid and the protein is a base rather than a slice. ' +
        (has('red curry paste')
          ? 'The curry paste is built for this: bloomed in fat, thinned, it carries everything.'
          : 'The savoury elements have far more room here than on a plate.'),
      w: 'The opposite trade. Forgiving to cook, harder to make feel like a composed dish rather than a bowl.',
    },
  ]
  const echoable = dish.find((d) =>
    ['allium', 'herb', 'fruit', 'veg'].includes(
      ING_CLASS[d.name] || ING_CLASS[d.name?.toLowerCase?.()]
    )
  )
  if (echoable) {
    D.push({
      t: 'One ingredient, three registers',
      b: `Take ${echoable.name} and use it in more than one state. Charred beneath, raw on top, and something in between — an oil, a pickle, a purée. The same element appearing in different registers is what separates a composed dish from a plate of ingredients.`,
      w: 'This is a compositional device, not a flavour one. It can also read as a gimmick if the states are not doing different jobs.',
    })
  }
  if (jobs['savoury depth']?.length) {
    D.push({
      t: 'Let the sauce be the dish',
      b: `Mole logic. ${focus} becomes the vehicle and ${jobs['savoury depth'][0]} — with whatever else you have — becomes the point. Seeds, nuts, or reduction supply the body instead of fat. The protein serves the sauce rather than the other way round.`,
      w: 'An inversion of roast logic. It changes the whole texture of the plate, and it demands a lot of the sauce.',
    })
  }
  return D
}

export function buildWriteUp(dish, form, anchor = anchorFor(null)) {
  const { jobs } = dishRead(dish, anchor)
  const formed = dish.filter((d) => d.mode)
  const unformed = dish.filter((d) => !d.mode)
  return {
    type: 'writeup',
    lead: `${anchor.name || 'Untitled'}${form ? ', ' + form.name.toLowerCase() : ''}.`,
    formed,
    unformed,
    jobs,
    unresolved: observations(dish, anchor).slice(0, 3),
  }
}
