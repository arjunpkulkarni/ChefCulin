/**
 * Group-level language for shared volatile compounds (§2.3).
 *
 * Group language is primary, per-compound odor descriptors are a bonus. That is
 * a structural choice, not a stopgap: IDF selects the rare compounds that make a
 * pairing distinctive, while published descriptors cover the well-studied common
 * ones, so named descriptors reach roughly 2 of the top 30 explanatory
 * compounds. "They share pyrroles and pyrazines" is the output a chef can use;
 * a descriptor is added only where the corpus has one.
 */

/** Groups collapsed to the phrase a cook would recognise. Unlisted groups pass through. */
const GROUP_PHRASE = {
  'Carbonyls, aldehydes': 'aldehydes',
  'Carbonyls, ketones': 'ketones',
  'Sulfur compounds': 'sulfur compounds',
  'Oxazol(in)es': 'oxazoles',
  Bases: 'pyrazines and pyridines',
  Esters: 'esters',
  Alcohols: 'alcohols',
  Furans: 'furans',
  Lactones: 'lactones',
  Phenols: 'phenols',
  Terpenes: 'terpenes',
  Hydrocarbons: 'hydrocarbons',
  Acids: 'acids',
  Ethers: 'ethers',
  Pyrroles: 'pyrroles',
}

export function groupPhrase(group) {
  if (!group) return 'unclassified compounds'
  return GROUP_PHRASE[group] || String(group).toLowerCase()
}

/**
 * Rank the compound groups behind a pairing, most-shared first.
 * @returns {{group: string, phrase: string, count: number, top_idf: number}[]}
 */
export function groupsFor(sharedCompounds = []) {
  const byGroup = new Map()
  for (const c of sharedCompounds) {
    const key = c.compound_group || 'Unclassified'
    const cur = byGroup.get(key) || { group: key, phrase: groupPhrase(key), count: 0, top_idf: 0 }
    cur.count += 1
    cur.top_idf = Math.max(cur.top_idf, c.idf || 0)
    byGroup.set(key, cur)
  }
  return [...byGroup.values()].sort((a, b) => b.count - a.count || b.top_idf - a.top_idf)
}

/**
 * One sentence naming what two ingredients actually share.
 * Returns null when there is nothing to say — the caller renders nothing
 * rather than a filler sentence.
 */
export function sharedCompoundSentence(sharedCompounds = [], { max = 3 } = {}) {
  const groups = groupsFor(sharedCompounds).slice(0, max)
  if (!groups.length) return null
  const phrases = groups.map((g) => g.phrase)
  const list =
    phrases.length === 1
      ? phrases[0]
      : `${phrases.slice(0, -1).join(', ')} and ${phrases[phrases.length - 1]}`
  return `Shares ${list}`
}

/** The individual compounds worth naming — highest IDF first, deduped. */
export function topCompounds(sharedCompounds = [], { limit = 5 } = {}) {
  const seen = new Set()
  return [...sharedCompounds]
    .sort((a, b) => (b.idf || 0) - (a.idf || 0))
    .filter((c) => {
      const k = c.compound_id || c.raw_compound
      if (seen.has(k)) return false
      seen.add(k)
      return true
    })
    .slice(0, limit)
}
