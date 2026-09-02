/**
 * Alias coverage measurement (scope doc Part 3).
 *
 * Tests names as a working chef would type them against the spine's member and
 * alias vocabulary. The number sizes the LLM entry point (§2.8) before the
 * architecture commits to it: a picker constrains people to valid options, free
 * text does not.
 *
 * The list below is a first pass written against the doc's own examples. It
 * needs a chef's review — the point of the exercise is that the names come from
 * how someone actually types, not from what the corpus happens to contain.
 *
 * Run:  node scripts/alias-coverage.mjs [--verbose]
 */
import { resolveIngredient } from '../src/lib/spineResolve.js'

/** [typed name, what it should reach] — the second field is a note, not asserted. */
const CHEF_NAMES = [
  // — the doc's own examples —
  ['vine toms', 'tomato'], ['san marzano', 'tomato'], ['maldon', 'salt'],
  ['banana shallots', 'shallot'], ['guanciale', 'cured pork'], ['espelette', 'chilli'],
  ['piquillos', 'pepper'], ['nduja', 'cured pork'], ['gochujang', 'fermented chilli paste'],
  ['yuzu kosho', 'yuzu + chilli'],
  // — plain names, should be easy —
  ['garlic', 'garlic'], ['onion', 'onion'], ['tomato', 'tomato'], ['carrot', 'carrot'],
  ['celery', 'celery'], ['leek', 'leek'], ['shallot', 'shallot'], ['chive', 'chive'],
  ['thyme', 'thyme'], ['rosemary', 'rosemary'], ['sage', 'sage'], ['basil', 'basil'],
  ['parsley', 'parsley'], ['coriander', 'coriander'], ['dill', 'dill'], ['mint', 'mint'],
  ['bay leaf', 'bay'], ['oregano', 'oregano'], ['tarragon', 'tarragon'], ['chervil', 'chervil'],
  ['lemon', 'lemon'], ['lime', 'lime'], ['orange', 'orange'], ['apple', 'apple'],
  ['pear', 'pear'], ['peach', 'peach'], ['cherry', 'cherry'], ['strawberry', 'strawberry'],
  ['raspberry', 'raspberry'], ['blackberry', 'blackberry'], ['blueberry', 'blueberry'],
  ['potato', 'potato'], ['mushroom', 'mushroom'], ['aubergine', 'eggplant'],
  ['courgette', 'zucchini'], ['pepper', 'pepper'], ['cucumber', 'cucumber'],
  ['spinach', 'spinach'], ['cabbage', 'cabbage'], ['cauliflower', 'cauliflower'],
  ['broccoli', 'broccoli'], ['fennel', 'fennel'], ['beetroot', 'beet'],
  // — plurals and casing —
  ['tomatoes', 'tomato'], ['onions', 'onion'], ['mushrooms', 'mushroom'],
  ['carrots', 'carrot'], ['Garlic', 'garlic'], ['CHERRIES', 'cherry'],
  ['strawberries', 'strawberry'], ['potatoes', 'potato'], ['anchovies', 'anchovy'],
  // — hyphenation and spacing —
  ['extra-virgin olive oil', 'olive oil'], ['extra virgin olive oil', 'olive oil'],
  ['spring onion', 'scallion'], ['star anise', 'star anise'], ['black pepper', 'pepper'],
  ['white pepper', 'pepper'], ['sea salt', 'salt'], ['olive oil', 'olive oil'],
  // — trade and regional names —
  ['scallions', 'spring onion'], ['cilantro', 'coriander'], ['rocket', 'arugula'],
  ['arugula', 'rocket'], ['eggplant', 'aubergine'], ['zucchini', 'courgette'],
  ['garbanzo', 'chickpea'], ['chickpeas', 'chickpea'], ['fava', 'broad bean'],
  ['mange tout', 'snow pea'], ['swede', 'rutabaga'], ['capsicum', 'pepper'],
  ['chilli', 'chilli'], ['chili', 'chilli'], ['chile', 'chilli'],
  // — proteins —
  ['chicken', 'chicken'], ['beef', 'beef'], ['pork', 'pork'], ['lamb', 'lamb'],
  ['duck breast', 'duck'], ['pork belly', 'pork'], ['chicken thigh', 'chicken'],
  ['short rib', 'beef'], ['rib eye', 'beef'], ['sirloin', 'beef'],
  ['bacon', 'bacon'], ['pancetta', 'cured pork'], ['prosciutto', 'cured pork'],
  ['chorizo', 'cured pork'], ['salmon', 'salmon'], ['cod', 'cod'],
  ['scallops', 'scallop'], ['prawns', 'prawn'], ['langoustine', 'langoustine'],
  ['squid', 'squid'], ['mussels', 'mussel'], ['oysters', 'oyster'],
  // — dairy, fat, pantry —
  ['butter', 'butter'], ['brown butter', 'butter'], ['double cream', 'cream'],
  ['creme fraiche', 'cream'], ['parmesan', 'parmesan'], ['parmigiano', 'parmesan'],
  ['gruyere', 'gruyere'], ['mascarpone', 'mascarpone'], ['yoghurt', 'yogurt'],
  ['buttermilk', 'buttermilk'], ['egg yolk', 'egg'], ['eggs', 'egg'],
  // — seasoning and ferment —
  ['soy', 'soy sauce'], ['soy sauce', 'soy sauce'], ['fish sauce', 'fish sauce'],
  ['miso', 'miso'], ['mirin', 'mirin'], ['sake', 'sake'], ['rice vinegar', 'vinegar'],
  ['sherry vinegar', 'vinegar'], ['balsamic', 'vinegar'], ['dijon', 'mustard'],
  ['capers', 'caper'], ['cornichons', 'gherkin'], ['tahini', 'sesame'],
  ['harissa', 'chilli paste'], ['ras el hanout', 'spice blend'], ['za atar', 'spice blend'],
  ['sumac', 'sumac'], ['saffron', 'saffron'], ['vanilla', 'vanilla'],
  ['cinnamon', 'cinnamon'], ['cardamom', 'cardamom'], ['clove', 'clove'],
  ['nutmeg', 'nutmeg'], ['mace', 'mace'], ['juniper', 'juniper'],
  ['smoked paprika', 'paprika'], ['pimenton', 'paprika'], ['cumin', 'cumin'],
  ['coriander seed', 'coriander'], ['fenugreek', 'fenugreek'], ['nigella', 'nigella'],
  // — other —
  ['walnut', 'walnut'], ['hazelnut', 'hazelnut'], ['almond', 'almond'],
  ['pistachio', 'pistachio'], ['pine nuts', 'pine nut'], ['honey', 'honey'],
  ['maple syrup', 'maple'], ['dark chocolate', 'cocoa'], ['cocoa', 'cocoa'],
  ['coffee', 'coffee'], ['green tea', 'tea'], ['white wine', 'wine'],
]

const verbose = process.argv.includes('--verbose')
const byTier = {}
const misses = []
let resolved = 0

for (const [typed, intent] of CHEF_NAMES) {
  const r = resolveIngredient(typed)
  if (r.state === 'resolved') {
    resolved += 1
    byTier[r.matched_on] = (byTier[r.matched_on] || 0) + 1
  } else {
    byTier[r.state] = (byTier[r.state] || 0) + 1
    misses.push({ typed, intent, state: r.state })
  }
}

const pct = ((resolved / CHEF_NAMES.length) * 100).toFixed(1)
console.log(`\nAlias coverage: ${resolved}/${CHEF_NAMES.length} = ${pct}%\n`)
console.log('By match tier:')
for (const [tier, n] of Object.entries(byTier).sort((a, b) => b[1] - a[1])) {
  console.log(`  ${String(tier).padEnd(10)} ${String(n).padStart(4)}`)
}

if (misses.length) {
  console.log(`\n${misses.length} unresolved:`)
  const width = Math.max(...misses.map((m) => m.typed.length))
  for (const m of misses) {
    console.log(`  ${m.typed.padEnd(width)}  → wanted: ${m.intent}`)
  }
}

if (verbose) {
  console.log('\nResolved detail:')
  for (const [typed] of CHEF_NAMES) {
    const r = resolveIngredient(typed)
    if (r.state === 'resolved') {
      console.log(`  ${typed.padEnd(26)} → ${r.display.padEnd(28)} [${r.matched_on}] ${r.spine_id}`)
    }
  }
}

console.log(
  `\nGate (§2.8): at ~70% extend aliases and ship the entry point; ` +
    `at ~25% the alias layer is its own workstream.\n`
)
