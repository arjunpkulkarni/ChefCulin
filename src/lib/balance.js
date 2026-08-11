import { ANCHOR, AXES, FRAMES } from '../data/domain.js'

/** Pure balance model for the dish sidebar. */
export function computeBalance(dish, form) {
  const base = form && FRAMES[form.name] ? FRAMES[form.name].fat : 0.6
  const t = {
    glut: ANCHOR.glut,
    nucl: ANCHOR.nucl,
    salt: 0,
    fat: base,
    acid: 0,
    sweet: 0,
    capsaicin: 0,
    pungent: 0,
    trigeminal: 0,
  }
  if (form && FRAMES[form.name].produces.includes('salt-cured')) t.salt += 1

  dish.forEach((d) => {
    const baseAx = AXES[d.name] || {}
    for (const k in baseAx) if (k in t) t[k] += baseAx[k]
    const add = d.axAdd || {}
    for (const k in add) if (k in t) t[k] += add[k]
  })

  const n = dish.length + 1
  const umamiHave = t.glut > 0 ? t.glut / n : 0
  const synergyOn = t.glut > 0 && t.nucl > 0

  const mechs = [
    { k: 'capsaicin', label: 'Capsaicin', v: t.capsaicin },
    { k: 'pungent', label: 'Volatile', v: t.pungent },
    { k: 'trigeminal', label: 'Tingling', v: t.trigeminal },
  ].filter((m) => m.v > 0)

  let heatTotal = 0
  let heatLabel = 'Heat'
  let heatResolved = false
  let heatNote = null
  if (mechs.length === 1) {
    heatTotal = mechs[0].v
    heatLabel = mechs[0].label
    heatResolved = true
    if (mechs[0].k === 'capsaicin')
      heatNote = {
        ax: 'heat',
        note: 'Capsaicin is lipophilic — fat and dairy genuinely mute it. This is the one pungency where that works.',
      }
    if (mechs[0].k === 'pungent')
      heatNote = {
        ax: 'heat',
        note: 'Volatile pungency — isothiocyanates, from wasabi, horseradish or mustard. Nasal rather than oral, and it dissipates. Fat does essentially nothing here; it simply leaves.',
      }
    if (mechs[0].k === 'trigeminal')
      heatNote = {
        ax: 'heat',
        note: 'This is trigeminal, not heat. Sanshool tingles and numbs; ginger warms. It is not burning, and balancing it with fat would do nothing — there is nothing to cut.',
      }
  } else if (mechs.length > 1) {
    heatTotal = mechs.reduce((a, m) => a + m.v, 0)
    heatLabel = mechs.map((m) => m.label).join(' + ')
    heatResolved = true
    heatNote = {
      ax: 'heat',
      note:
        'Two different pungency mechanisms are in play — ' +
        mechs.map((m) => m.label.toLowerCase()).join(' and ') +
        '. They do not compound with each other and they do not respond to the same correction. Fat mutes capsaicin only.',
    }
  }

  const widths = {
    umami: Math.min(100, umamiHave * 100 * (synergyOn ? 2.2 : 1)),
    salt: Math.min(100, (t.salt / n) * 100),
    fat: Math.min(100, (t.fat / n) * 100),
    acid: Math.min(100, (t.acid / n) * 100),
    sweet: Math.min(100, (t.sweet / n) * 100),
    heat: Math.min(100, (heatTotal / n) * 100),
  }

  const synGhost =
    !synergyOn && t.glut > 0
      ? {
          left: Math.min(100, umamiHave * 100),
          width: Math.min(100 - umamiHave * 100, umamiHave * 100 * 1.2),
        }
      : null

  if (dish.length < 3) {
    return {
      widths,
      synergyOn,
      synGhost,
      umamiLabel: synergyOn ? 'Umami ×' : 'Umami',
      heatLabel,
      heatResolved,
      umamiResolved: synergyOn,
      flagged: null,
      msgClass: 'bal-gate',
      msg: `Balance check begins at 3 ingredients. (${dish.length}/3)`,
    }
  }

  const flags = []
  const addedGlut = t.glut - ANCHOR.glut
  if (addedGlut > 0) {
    flags.push({
      ax: 'umami',
      note: 'The duck already brings a nucleotide — it is a red meat, and inosinate rises further with searing and ageing. So a glutamate ingredient added to duck is not accumulating umami, it is amplifying it: glutamate plus nucleotide is roughly an order of magnitude, not a sum. This is the dashi principle, and the duck is doing what the bonito does.',
    })
  } else if (t.nucl > 0 && addedGlut === 0) {
    flags.push({
      ax: 'umami',
      note: 'Duck carries inosinate but little free glutamate. The hatched bar is the amplification sitting unclaimed — a glutamate source (miso, soy, aged cheese, tomato, kombu) multiplies the savoury depth far beyond what another meaty ingredient would.',
    })
  }
  if (heatNote) flags.push(heatNote)
  if (t.acid / n >= 0.4 && t.sweet < t.acid) {
    flags.push({
      ax: 'acid',
      note: 'Trending acidic with little to offset it. Sugars suppress perceived tartness and acids suppress perceived sweetness — a documented mutual suppression. Or reach for a drying, tannic reset instead.',
    })
  }
  if (t.salt / n >= 0.45) {
    flags.push({
      ax: 'salt',
      note: 'Salt building. Fat suppresses perceived saltiness — only free sodium ions reach the receptor, and fat impedes their release from the matrix. Note this runs one way only.',
    })
  }
  if (t.fat / n >= 0.55 && t.acid === 0) {
    flags.push({
      ax: 'fat',
      note: 'Rich, with no reset committed. Sourness brightens; astringency dries — different mechanisms, so which do you want? Salt will not cut this; that pair only runs the other way.',
    })
  }

  if (!flags.length) {
    return {
      widths,
      synergyOn,
      synGhost,
      umamiLabel: synergyOn ? 'Umami ×' : 'Umami',
      heatLabel,
      heatResolved,
      umamiResolved: synergyOn,
      flagged: null,
      msgClass: 'bal-gate',
      msg: 'Nothing trending. Keep building.',
    }
  }
  const f = flags[0]
  return {
    widths,
    synergyOn,
    synGhost,
    umamiLabel: synergyOn ? 'Umami ×' : 'Umami',
    heatLabel,
    heatResolved,
    umamiResolved: synergyOn,
    flagged: f.ax,
    msgClass: 'bal-note',
    msg: f.note,
  }
}

export function phaseOf(dish) {
  const formed = dish.filter((d) => d.mode).length
  const total = dish.length
  if (!total) {
    return {
      className: 'phase search',
      label: 'Gathering',
      text: 'Pull ingredients from the lenses. Give them forms whenever you are ready — or not at all.',
    }
  }
  if (formed < total) {
    return {
      className: 'phase compose',
      label: 'Composing',
      text: `${formed} of ${total} have a form. An ingredient can appear more than once — charred beneath, raw on top.`,
    }
  }
  return {
    className: 'phase done',
    label: 'Every element has a form',
    text: 'Nothing here says the dish is finished. That is your call.',
  }
}
