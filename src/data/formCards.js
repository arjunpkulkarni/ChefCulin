/**
 * Process frames keyed by culinary family of the focus ingredient.
 * Meat-centrepiece frames stay available for animal foods; produce, herbs and
 * dairy get their own set so Form is not a leftover duck confit menu.
 */
import { lookupIngredient } from './ingredients.js'

const card = (name, title, desc, craft) => ({ name, title, desc, craft })

export const FORM_LIBRARY = {
  Seared: card('Seared', 'Seared — surface browning, intact piece', 'High heat, surface browning; intact piece, jus or pan sauce.', [
    { k: 'Texture', v: 'browned exterior against a juicier interior' },
    { k: 'Temp', v: 'hot, rested, sliced or plated whole' },
    { k: 'Sauce', v: 'pan jus, reduction, or none' },
  ]),
  Confit: card('Confit', 'Confit — fat as cooking medium', 'Slow cook in fat; preserved, shreddable, later crispable.', [
    { k: 'Texture', v: 'spoon-tender, later crispable' },
    { k: 'Temp', v: 'reheated, crisped, or cold' },
    { k: 'Sauce', v: 'fat is the medium, not an addition' },
  ]),
  'Crisp-skinned roast': card('Crisp-skinned roast', 'Crisp-skinned roast — skin or crust engineering', 'Oven or spit; skin or crust is the technical problem.', [
    { k: 'Texture', v: 'lacquered or shatteringly crisp exterior' },
    { k: 'Temp', v: 'hot, carved to order' },
    { k: 'Sauce', v: 'glaze, condiment, or pan jus' },
  ]),
  'Cold salted': card('Cold salted', 'Cold salted — restraint instead of roast', 'Salt and chill over browning; clean, sliced, restrained.', [
    { k: 'Texture', v: 'firm, sliceable, clean' },
    { k: 'Temp', v: 'cold or barely warm' },
    { k: 'Sauce', v: 'dipping, dressing, condiment' },
  ]),
  'Broth system': card('Broth system', 'Broth system — richness becomes structure', 'Ingredient as base in liquid; broth is the sauce; communal.', [
    { k: 'Texture', v: 'yielding solids, liquid body' },
    { k: 'Temp', v: 'hot, communal, sustained' },
    { k: 'Sauce', v: 'the broth is the sauce' },
  ]),
  Braise: card('Braise', 'Braise — long cook, sauce from the liquid', 'Long and low in liquid; braising liquid becomes the sauce.', [
    { k: 'Texture', v: 'shredding, gelatinous, spoon-yielding' },
    { k: 'Temp', v: 'long, low, hot at service' },
    { k: 'Sauce', v: 'the braising liquid becomes the sauce' },
  ]),
  Ground: card('Ground', 'Ground — dispersed fat, mixed seasoning', 'Fat dispersed through the mass; ragù, sausage, dumpling fillings.', [
    { k: 'Texture', v: 'fat dispersed, not layered' },
    { k: 'Fat ratio', v: 'fat ground in, or trimmed out' },
    { k: 'Binding', v: 'egg, panade, or nothing' },
  ]),
  Cured: card('Cured', 'Cured — salt, time, slice', 'Salt and time; sliced thin; pantry item more than plated centrepiece.', [
    { k: 'Texture', v: 'dense, sliceable, chewy' },
    { k: 'Temp', v: 'cold or room temperature' },
    { k: 'Time', v: 'days to weeks; make-ahead by definition' },
  ]),
  Smoked: card('Smoked', 'Smoked — phenols in the matrix', 'Smoke phenols carried in fat or surface; cold or hot smoke.', [
    { k: 'Texture', v: 'varies — cold-smoked stays raw; hot-smoked cooks' },
    { k: 'Aroma', v: 'smoke phenols in fat or on the surface' },
    { k: 'Fuel', v: 'fruitwood, tea and rice, hay, pine' },
  ]),
  'Terrine / rillette': card('Terrine / rillette', 'Terrine / rillette — fat as binder', 'Fat as binder; spreadable or sliceable; cold; needs acid alongside.', [
    { k: 'Texture', v: 'spreadable to sliceable, depending on set' },
    { k: 'Temp', v: 'cold; served from the fridge' },
    { k: 'Sauce', v: 'none — needs acid alongside, not on top' },
  ]),
  'Raw / tartare': card('Raw / tartare', 'Raw — tartare, carpaccio, crudo', 'No heat; acid, salt and fat carry it. Sourcing is the constraint.', [
    { k: 'Texture', v: 'yielding, dense, cool' },
    { k: 'Temp', v: 'cold' },
    { k: 'Seasoning', v: 'acid, salt and fat do all the work' },
  ]),
  Poached: card('Poached', 'Poached — gentle liquid, intact piece', 'Bare simmer; the cooking liquid seasons and keeps the piece intact.', [
    { k: 'Texture', v: 'tender, moist, no crust' },
    { k: 'Temp', v: 'just-cooked, served warm or chilled' },
    { k: 'Sauce', v: 'the poaching liquid, reduced or as a vinaigrette' },
  ]),
  Steamed: card('Steamed', 'Steamed — vapour, clean flavour', 'No browning; water-soluble aromatics stay put; texture is the problem.', [
    { k: 'Texture', v: 'tender, moist, unbrowned' },
    { k: 'Temp', v: 'hot, served immediately' },
    { k: 'Seasoning', v: 'after, or in the steaming liquid' },
  ]),
  Grilled: card('Grilled', 'Grilled — direct fire, char', 'Radiant heat and smoke; char is a flavour, not an accident.', [
    { k: 'Texture', v: 'charred edges, juicier interior' },
    { k: 'Aroma', v: 'phenolics from the fire' },
    { k: 'Sauce', v: 'glaze, salsa, or nothing' },
  ]),
  Roasted: card('Roasted', 'Roasted — dry heat, concentration', 'Water leaves; sugars concentrate; a browned surface if the piece allows it.', [
    { k: 'Texture', v: 'concentrated, browned where it touches heat' },
    { k: 'Temp', v: 'hot, or room temperature as a component' },
    { k: 'Sauce', v: 'pan juices, or eaten as-is' },
  ]),
  Charred: card('Charred', 'Charred — hard heat, Maillard', 'Surface goes past brown into bitter-sweet. The interior can stay raw.', [
    { k: 'Texture', v: 'blistered or blackened exterior' },
    { k: 'Aroma', v: 'carbon and caramel, not just roast' },
    { k: 'Use', v: 'whole, cut, or smashed into a dressing' },
  ]),
  Pickled: card('Pickled', 'Pickled — acid as the cooking medium', 'Vinegar or brine does the work. The ingredient becomes a reset, not a bulk.', [
    { k: 'Texture', v: 'crisp or yielding, depending on time' },
    { k: 'Temp', v: 'cold' },
    { k: 'Job', v: 'acid and crunch between richer bites' },
  ]),
  Puréed: card('Puréed', 'Puréed — smooth carrier', 'Cell walls broken; fat or liquid makes a base rather than a garnish.', [
    { k: 'Texture', v: 'smooth, spoonable' },
    { k: 'Job', v: 'a bed, a sauce, or a filling' },
    { k: 'Enrichment', v: 'butter, oil, stock — or none' },
  ]),
  Dried: card('Dried', 'Dried — water gone, flavour concentrated', 'Dehydration concentrates sugar, acid and aroma. Rehydrate, grind, or eat as chew.', [
    { k: 'Texture', v: 'leathery, crisp, or powder' },
    { k: 'Use', v: 'snack, infusion, or rebuilt in liquid' },
    { k: 'Time', v: 'hours to weeks' },
  ]),
  Infused: card('Infused', 'Infused — flavour into a medium', 'The ingredient seasons fat, water, alcohol or vinegar rather than sitting on the plate.', [
    { k: 'Medium', v: 'oil, butter, stock, syrup, or spirit' },
    { k: 'Time', v: 'minutes (hot) to days (cold)' },
    { k: 'After', v: 'strain, or leave the solids in' },
  ]),
  'Bloomed in fat': card('Bloomed in fat', 'Bloomed in fat — fat-soluble aromatics', 'Spices and pastes hit hot fat so the aroma spreads through the dish.', [
    { k: 'Texture', v: 'the spice is no longer dusty or raw' },
    { k: 'Timing', v: 'early, before liquid goes in' },
    { k: 'Risk', v: 'burned spice is bitter — keep it moving' },
  ]),
  'Fresh garnish': card('Fresh garnish', 'Fresh — uncooked, last on', 'Volatile aromatics intact. Heat would drive them off.', [
    { k: 'Texture', v: 'leafy, juicy, or a fine mince' },
    { k: 'Timing', v: 'after the heat is off' },
    { k: 'Job', v: 'lift, not bulk' },
  ]),
  Toasted: card('Toasted', 'Toasted — dry heat on the ingredient itself', 'Maillard in the spice, nut or grain — nuttier, rounder, less raw.', [
    { k: 'Texture', v: 'fragrant, slightly drier' },
    { k: 'Timing', v: 'before grinding or before liquid' },
    { k: 'Endpoint', v: 'aroma, not colour for its own sake' },
  ]),
  Boiled: card('Boiled', 'Boiled — water as the medium', 'Neutral, absorbent cooking. The liquid can be kept or thrown.', [
    { k: 'Texture', v: 'softened, hydrated' },
    { k: 'Job', v: 'carrier for sauce and fat' },
    { k: 'Liquid', v: 'seasoned water, milk, or stock' },
  ]),
  Melted: card('Melted', 'Melted — fat or dairy as a sauce', 'The ingredient becomes the coating rather than a piece on the plate.', [
    { k: 'Texture', v: 'fluid, gloss' },
    { k: 'Temp', v: 'warm enough to stay liquid' },
    { k: 'Job', v: 'nappe, emulsion, or dip' },
  ]),
  Whipped: card('Whipped', 'Whipped — air and cold', 'Aeration mutes aroma; season harder than seems right.', [
    { k: 'Texture', v: 'light, cold, spreadable' },
    { k: 'Temp', v: 'chilled' },
    { k: 'Seasoning', v: 'salt and acid read quieter when cold' },
  ]),
  Cultured: card('Cultured', 'Cultured — acid from fermentation', 'The ingredient is already a process: yoghurt, cheese, crème fraîche.', [
    { k: 'Texture', v: 'set, spoonable, or sliceable' },
    { k: 'Acid', v: 'lactic, not vinegar' },
    { k: 'Job', v: 'sauce, marinade, or the plate itself' },
  ]),
  'Fresh / raw': card('Fresh / raw', 'Fresh / raw — uncooked, intact chemistry', 'Acid, sweetness, crunch or juice as they are. No Maillard.', [
    { k: 'Texture', v: 'juicy, crisp, or yielding' },
    { k: 'Temp', v: 'cold or room temperature' },
    { k: 'Seasoning', v: 'salt, acid, oil — contact only' },
  ]),
}

const names = (...keys) => keys.map((k) => FORM_LIBRARY[k]).filter(Boolean)

const MEAT = names(
  'Seared',
  'Confit',
  'Crisp-skinned roast',
  'Braise',
  'Broth system',
  'Ground',
  'Cured',
  'Smoked',
  'Terrine / rillette',
  'Raw / tartare',
  'Cold salted',
  'Grilled',
  'Poached'
)

const AQUATIC = names(
  'Seared',
  'Poached',
  'Steamed',
  'Grilled',
  'Raw / tartare',
  'Broth system',
  'Cured',
  'Smoked'
)

const FRUIT = names('Fresh / raw', 'Roasted', 'Pickled', 'Puréed', 'Dried', 'Infused', 'Charred')
const VEG = names('Roasted', 'Charred', 'Fresh / raw', 'Pickled', 'Steamed', 'Puréed', 'Broth system')
const HERB = names('Fresh garnish', 'Infused', 'Bloomed in fat', 'Dried', 'Charred')
const SPICE = names('Bloomed in fat', 'Toasted', 'Ground', 'Infused', 'Cured')
const NUT = names('Toasted', 'Ground', 'Roasted', 'Infused', 'Puréed')
const DAIRY = names('Fresh / raw', 'Melted', 'Whipped', 'Infused', 'Cultured')
const CEREAL = names('Boiled', 'Steamed', 'Toasted', 'Puréed', 'Ground')
const SOY = names('Fresh / raw', 'Broth system', 'Infused', 'Ground', 'Braise')
const SWEET = names('Melted', 'Infused', 'Fresh / raw', 'Toasted')

/** Backward-compatible default list (animal centrepiece). */
export const FORM_CARDS = MEAT

export function formsForIngredient(name) {
  const row = lookupIngredient(name)
  const group = row?.food_group || ''
  const sub = row?.food_subgroup || ''
  const blob = `${name} ${group} ${sub}`.toLowerCase()

  if (/capsicum|chile|chili|pepper \(c/i.test(blob)) return SPICE
  if (/herb/i.test(sub) || (/herbs and spices/i.test(group) && /herb/i.test(sub))) return HERB
  if (/spice|seasoning/i.test(sub) || group === 'Herbs and Spices') {
    if (/herb/i.test(sub)) return HERB
    return SPICE
  }
  if (group === 'Fruits') return FRUIT
  if (group === 'Vegetables' || group === 'Gourds') {
    if (/onion/i.test(sub) || /garlic/i.test(blob)) return names('Fresh / raw', 'Charred', 'Pickled', 'Infused', 'Roasted')
    return VEG
  }
  if (group === 'Aquatic foods') return AQUATIC
  if (group === 'Animal foods') return MEAT
  if (group === 'Nuts' || /oilseed/i.test(sub)) return NUT
  if (group === 'Milk and milk products') return DAIRY
  if (group === 'Cereals and cereal products' || group === 'Baking goods' || group === 'Pulses') return CEREAL
  if (group === 'Soy') return SOY
  if (group === 'Cocoa and cocoa products' || group === 'Confectioneries') return SWEET
  if (group === 'Beverages') return names('Infused', 'Fresh / raw', 'Reduced')
  return VEG
}
