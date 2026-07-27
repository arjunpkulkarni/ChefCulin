/* FORM DETERMINES PROPERTIES. Zest is aromatic oil (terpenes) and carries no acid;
     the acid is in the juice. Lemon zest is not lemon juice. Roasted garlic is not raw
     garlic. Tagging by ingredient NAME rather than ingredient-in-a-FORM is a modelling
     error — the same gap that made confit look skinless. */
  const AXES = {
    'rosemary':{}, 'juniper':{}, 'bay':{}, 'bergamot':{}, 'orange peel':{}, 'spruce':{}, 'fir':{},
    'roasted onion':{glut:1,sweet:1}, 'black garlic':{glut:1,sweet:1}, 'miso':{glut:1,salt:1},
    'porcini':{glut:1,nucl:1}, 'shiitake':{glut:1,nucl:1}, 'toasted grain':{}, 'cocoa':{},
    'verjus':{acid:1}, 'cider vinegar':{acid:1}, 'tart cherry':{acid:1,sweet:1}, 'blood orange':{acid:1,sweet:1},
    'black tea':{}, 'wine reduction':{acid:1}, 'pomegranate':{acid:1,sweet:1},
    'pancake':{}, 'cucumber':{}, 'scallion':{}, 'sweet bean sauce':{sweet:1,glut:1,salt:1}, 'radish':{},
    'fermented bean curd':{glut:1,salt:1}, 'taro':{}, 'water spinach':{}, 'ginger':{trigeminal:1}, 'rice noodle':{},
    'coconut milk':{fat:1,sweet:1}, 'red curry paste':{capsaicin:1,salt:1,glut:1}, 'lychee':{sweet:1},
    'thai basil':{}, 'makrut lime leaf':{},
    'vinegar':{acid:1}, 'cherry':{acid:1,sweet:1}, 'pickled shallot':{acid:1}, 'cabbage':{},
    'potato':{}, 'white bean':{}, 'bread':{}, 'rice':{}, 'dumpling':{},
    'soy':{glut:1,salt:1}, 'red wine':{acid:1}, 'mushroom':{glut:1,nucl:1}, 'duck jus':{glut:1,nucl:1,fat:1},
    'pappardelle':{}, 'soffritto':{sweet:1}, 'tomato':{acid:1,glut:1}, 'sage':{}, 'parmesan':{glut:1,nucl:1,salt:1,fat:1},
    'bitter orange':{acid:1}, 'gastrique':{acid:1,sweet:1}, 'wine vinegar':{acid:1},
    'ancho chile':{capsaicin:1}, 'pumpkin seed':{fat:1}, 'tomatillo':{acid:1}, 'cinnamon':{}, 'sesame':{fat:1},
    'red cabbage':{acid:1}, 'apple':{sweet:1,acid:1}, 'caraway':{},
    'thyme':{}, 'sage':{}, 'lavender':{}, 'makrut lime':{}, 'cardamom':{}, 'pink peppercorn':{trigeminal:1}, 'star anise':{},
    'coffee':{}, 'fish sauce':{glut:1,nucl:1,salt:1}, 'aged cheese':{glut:1,nucl:1,salt:1,fat:1}, 'dried shrimp':{glut:1,nucl:1,salt:1}, 'yeast extract':{glut:1,salt:1},
    'sumac':{acid:1}, 'tamarind':{acid:1,sweet:1}, 'green apple':{acid:1,sweet:1}, 'sorrel':{acid:1}, 'pickled walnut':{acid:1},
    'hoisin':{sweet:1,glut:1,salt:1}, 'garlic paste':{}, 'sugar':{sweet:1},
    'lettuce cup':{}, 'crepe':{}, 'pickled cucumber':{acid:1}, 'black vinegar':{acid:1}, 'chive oil':{fat:1}, 'shiso':{},
    'mustard greens':{}, 'coconut water':{sweet:1}, 'chile':{capsaicin:1}, 'lime':{acid:1},
    'white beans':{}, 'fennel':{}, 'kale':{}, 'celeriac':{}, 'rice ferment':{glut:1},
    'pineapple':{sweet:1,acid:1}, 'cherry tomato':{acid:1,glut:1}, 'galangal':{trigeminal:1},
    'grape':{sweet:1}, 'apricot':{sweet:1,acid:1}, 'peanut':{fat:1}, 'curry leaf':{}, 'coconut cream':{fat:1,sweet:1},
    'celery':{}, 'carrot':{sweet:1},
    'pecorino':{glut:1,nucl:1,salt:1,fat:1}, 'chestnut':{sweet:1}, 'black olive':{salt:1,glut:1}, 'orange zest':{}, 'anchovy':{glut:1,nucl:1,salt:1},
    'shallot':{}, 'stock':{glut:1,nucl:1},
    'blood orange':{acid:1,sweet:1}, 'quince':{sweet:1,acid:1}, 'sour cherry':{acid:1,sweet:1}, 'pomegranate molasses':{acid:1,sweet:1}, 'grapefruit':{acid:1},
    'pasilla chile':{capsaicin:1}, 'almond':{fat:1}, 'clove':{}, 'raisin':{sweet:1},
    'hazelnut':{fat:1}, 'walnut':{fat:1}, 'prune':{sweet:1}, 'smoked paprika':{capsaicin:1},
    'marjoram':{}, 'bacon':{salt:1,fat:1,glut:1}, 'vinegar':{acid:1},
    'rye bread':{}, 'horseradish':{pungent:1}, 'lingonberry':{acid:1,sweet:1}, 'buckwheat':{},
    'orange':{acid:1,sweet:1}, 'plum':{acid:1,sweet:1}, 'sauerkraut':{acid:1},
    'lentils':{}, 'polenta':{}, 'barley':{},
    'port':{sweet:1}, 'bone broth':{glut:1,nucl:1}
  };
  const COLORS = { compound:'var(--skin)', tradition:'var(--sage)', 'co-occurrence':'var(--plum)' };

  /* ============================================================
     DESIGN FRAMES — structural properties, not prose.
     `produces` = what this state actually yields.
     `absent`   = what it structurally does NOT yield.
     Tension is DERIVED by comparing a thread's `requires`
     against the committed frame's produces/absent. Nothing
     below is hand-authored per combination.
     ============================================================ */
  const FRAMES = {
    'Seared magret':      { produces:['crisp-skin','rendered-fat','intact-roast','rendered-jus'], absent:['dispersed-fat','long-cook','chopped-meat'], overlay:'sear',   fat:0.75 },
    'Crisp-skinned roast':{ produces:['crisp-skin','rendered-fat','intact-roast','rendered-jus'], absent:['dispersed-fat','chopped-meat'],             overlay:'roast',  fat:0.8  },
    /* Confit legs are routinely finished skin-down in a hot pan until crisp. The
       preservation stage and the finishing stage produce different properties —
       a frame is a PROCESS, not a settled end-state. Confit can absolutely be crisp. */
    'Confit':             { produces:['tender','fat-medium','salt-cured','long-cook','crisp-skin'], absent:['rendered-jus','intact-roast'], overlay:'confit', fat:0.95 },
    'Cold salted':        { produces:['salt-cured','firm','cold'],                                absent:['crisp-skin','rendered-fat','rendered-jus'], overlay:'cure',   fat:0.4  },
    'Broth system':       { produces:['dispersed-fat','liquid-body','long-cook','tender'],        absent:['crisp-skin','rendered-jus','intact-roast'], overlay:'broth',  fat:0.35 },
    'Braise':             { produces:['tender','long-cook','dispersed-fat','sauce-medium'],       absent:['crisp-skin','intact-roast'],                overlay:'braise', fat:0.6  },
    'Ground':             { produces:['dispersed-fat','chopped-meat','sauce-medium','long-cook'], absent:['crisp-skin','intact-roast','rendered-jus'], overlay:'ground', fat:0.55 },
    'Cured':              { produces:['salt-cured','firm','cold','dense'],                        absent:['crisp-skin','rendered-fat','tender'],       overlay:'cure',   fat:0.5  },
    'Smoked':             { produces:['smoke-phenols','rendered-fat'],                            absent:['fresh-crunch'],                             overlay:'smoke',  fat:0.7  },
    'Terrine / rillette': { produces:['fat-medium','cold','dense','tender'],                      absent:['crisp-skin','rendered-jus','intact-roast'], overlay:'terrine',fat:0.9  },
    'Raw / tartare':      { produces:['cold','chopped-meat','firm'],                              absent:['crisp-skin','rendered-fat','long-cook'],    overlay:'raw',    fat:0.35 }
  };

  /* Reusable behaviour overlays — authored ONCE per frame type, inherited by
     every ingredient. Not per-combination. This is what makes it scale. */
  const OVERLAYS = {
    sear:    'Surface aromatics. The fat cap renders fast and carries aroma at the skin — herbs and citrus perfume the outside, they do not infuse the meat.',
    roast:   'Cavity and surface. Aromatics work on the skin, in the cavity, or in the pan juices — three different jobs in one frame.',
    confit:  'Infusion, not surface. Everything here spends hours in fat at low heat — aromatics infuse the medium rather than perfuming a surface. Delicate volatiles will be lost; robust ones deepen.',
    cure:    'Dry contact. No cooking medium to carry aroma — aromatics work by direct contact with salt, or afterwards as a dressing. Water leaves; flavour concentrates.',
    broth:   'Dispersion and timing. Aromatics disperse through liquid and can go muddy if over-extracted. When something goes in matters as much as whether it goes in.',
    braise:  'Long extraction. Robust aromatics survive and deepen; delicate ones vanish in the first hour. Late additions do different work from early ones.',
    ground:  'Distributed, not layered. Aromatics are mixed through the meat rather than sitting on it — seasoning is even, and there is no surface to perfume.',
    smoke:   'Fat carries phenols. Smoke compounds are fat-soluble, so the same rendered-fat phase that carries terpenes carries smoke — they will compete for the same channel.',
    terrine: 'Cold and set. Aroma is muted by cold and fat; season harder than seems right, and expect acid to be needed alongside, not on top.',
    raw:     'No heat, no extraction. Aromatics work by contact, cut size and surface area alone. Acid, salt and fat do all the carrying.'
  };

  const PROP_LABELS = {
    'crisp-skin':'crisp skin', 'fresh-crunch':'fresh crunch', 'soft-carrier':'a soft carrier',
    'dispersed-fat':'fat dispersed into the dish', 'liquid-body':'a liquid body',
    'chopped-meat':'chopped or shredded meat', 'sauce-medium':'a sauce medium',
    'rendered-jus':'rendered jus', 'intact-roast':'an intact roast', 'long-cook':'long cooking',
    'rendered-fat':'rendered fat', 'dark-meat':'dark meat'
  };

  /* The anchor is not inert. Duck is a red meat: it carries inosinate (a NUCLEOTIDE),
     real savoury depth, and generates Maillard volatiles when seared. Treating the
     anchor as contributing only "fat" was a hole — and it interacts directly with the
     umami synergy: duck ALREADY brings a nucleotide to the table. */
  const ANCHOR = { name:'duck breast', glut:1, nucl:1, fat:1 };


  /* ============================================================
     DELIVERY MODES — the second search space.
     Not "what ingredients" but "what do you DO with them".
     Same ingredient, different form, different axis contribution.
     A chef can commit ONE ingredient in SEVERAL modes — charred
     scallion oil beneath, raw scallion on top. That is composition,
     and no pairing tool can represent it.
     ============================================================ */
  const DELIVERY = {
    /* axAdd = what the TRANSFORMATION creates that was not there before.
       Most modes add nothing — they change intensity and placement, not chemistry.
       Curry paste is capsaicin, salt and glutamate whether it is a rub or a sauce. */
    'red curry paste': [
      {mode:'Sauce base',        note:'Bloomed in fat, thinned with coconut. Aromatics disperse; the heat spreads through the whole dish rather than sitting on the protein.', axAdd:{fat:1}},
      {mode:'Broth',             note:'Diluted and simmered. Lower intensity, longer reach — background rather than statement.', axAdd:{}},
      {mode:'Rub, wiped before searing', note:'Aromatics hit the sear and enter the Maillard. Concentrated at the surface, almost none in the interior.', axAdd:{}},
      {mode:'Folded into a purée',       note:'Diluted by starch and sweetness. Squash blunts the heat and lengthens it.', axAdd:{sweet:1}},
      {mode:'Marinade',          note:'Penetrates over time; the salt does work on the protein as well as the flavour.', axAdd:{}}
    ],
    'scallion': [
      {mode:'Raw, sliced',       note:'Sharp allium bite, fresh and green. A cutting element.', axAdd:{}},
      {mode:'Charred',           note:'Sugars caramelise. The bite goes; sweetness and Maillard depth arrive that were not there before — this is a real change, not just an intensity one.', axAdd:{sweet:1, glut:1}},
      {mode:'Charred scallion oil', note:'The char carried in fat — aroma spreads through the dish rather than sitting on it.', axAdd:{sweet:1, glut:1, fat:1}},
      {mode:'Chimichurri / pesto', note:'Cut with acid and oil. Now a sauce with structure, not a garnish.', axAdd:{fat:1, acid:1}},
      {mode:'Confited in fat',   note:'Soft, sweet, silky. No bite at all.', axAdd:{fat:1, sweet:1}}
    ],
    'orange peel': [
      {mode:'Fresh zest',        note:'Volatile terpene oils at their brightest. Add late — heat drives them off.', axAdd:{}},
      {mode:'Infused in fat',    note:'The lipid phase captures the terpenes and releases them slowly. The lipid-phase principle in practice.', axAdd:{fat:1}},
      {mode:'Candied',           note:'Sugar enters the ingredient. A texture as much as a flavour.', axAdd:{sweet:1}},
      {mode:'Dried and ground',  note:'Concentrated, slightly bitter. Survives long cooking where fresh zest would not.', axAdd:{}},
      {mode:'In a gastrique',    note:'Sugar and vinegar reduced around it. Now structural — and now genuinely acidic, which the peel alone is not.', axAdd:{acid:1, sweet:1}}
    ],
    'miso': [
      {mode:'Glaze',             note:'Painted on and caramelised. Sugars brown at the surface.', axAdd:{sweet:1}},
      {mode:'In a sauce',        note:'Dispersed. Savoury depth throughout rather than concentrated.', axAdd:{}},
      {mode:'Marinade / cure',   note:'Salt and enzymes work into the protein over days. Texture changes, not just flavour.', axAdd:{}},
      {mode:'Whisked into butter', note:'Fat carries it; a finishing element rather than a base.', axAdd:{fat:1}}
    ],
    'cherry': [
      {mode:'Fresh / raw',       note:'Acid and sweet, juicy, cutting.', axAdd:{}},
      {mode:'Pickled',           note:'Vinegar enters the fruit. Genuinely more acidic than it was.', axAdd:{acid:1}},
      {mode:'Reduced into a sauce', note:'Water leaves; sugars concentrate. Body and gloss arrive.', axAdd:{sweet:1}},
      {mode:'Dried',             note:'Concentrated sweetness and a chew.', axAdd:{sweet:1}}
    ]
  };

  /* Delivery modes belong to a CLASS of ingredient, not to all ingredients.
     Wine is not "charred." A herb is not "reduced." A generic menu applied
     to everything is a category error. */
  const CLASS_DELIVERY = {
    liquid_alcohol: [   // wine, port, spirits
      {mode:'Reduced',       note:'Water and alcohol drive off; acid and sugar concentrate. Body and gloss arrive.', axAdd:{sweet:1}},
      {mode:'Deglazed into a pan', note:'Lifts the fond — the browned residue becomes part of the sauce. This is where the Maillard the sear built actually gets used.', axAdd:{glut:1}},
      {mode:'Macerated / soaked into fruit', note:'Carries alcohol and tannin into something else rather than standing alone.', axAdd:{}},
      {mode:'Braising liquid',  note:'Long, slow, dilute. The wine becomes background structure rather than a statement.', axAdd:{}},
      {mode:'Raw, as an acid finish', note:'Uncooked, sharp, with the alcohol still present. Rare — and deliberate.', axAdd:{acid:1}}
    ],
    vinegar_acid: [     // vinegar, verjus
      {mode:'Raw / finishing', note:'Added off-heat. Full sharpness intact.', axAdd:{}},
      {mode:'Reduced / gastrique', note:'Cooked with sugar until syrupy. Sour and sweet become one structure with body.', axAdd:{sweet:1}},
      {mode:'Pickling liquid', note:'Carries acid into something else — the vinegar becomes a delivery vehicle rather than an ingredient.', axAdd:{}},
      {mode:'In a vinaigrette', note:'Emulsified with fat. The fat blunts the edge and carries it further.', axAdd:{fat:1}},
      {mode:'Deglazed',        note:'Sharp and volatile — much of the acid cooks off, leaving the aromatic behind.', axAdd:{}}
    ],
    allium: [           // scallion, shallot, garlic, onion
      {mode:'Raw, sliced',   note:'Sharp, sulfurous bite. A cutting element.', axAdd:{}},
      {mode:'Charred',       note:'Sugars caramelise; the bite goes. Sweetness and Maillard depth arrive that were not there before.', axAdd:{sweet:1, glut:1}},
      {mode:'Slow-cooked / confited', note:'Soft, sweet, silky. Sulfur compounds break down entirely.', axAdd:{sweet:1, fat:1}},
      {mode:'Pickled',       note:'Acid enters; the bite becomes bright rather than harsh.', axAdd:{acid:1}},
      {mode:'As an oil',     note:'Carried in fat and spread through the dish rather than sitting on it.', axAdd:{fat:1}}
    ],
    herb: [             // rosemary, thyme, basil, sage
      {mode:'Fresh, finishing', note:'Volatile aromatics intact. Add late — heat drives them off.', axAdd:{}},
      {mode:'Infused in fat',  note:'The lipid phase captures the terpenes and releases them slowly. This is the lipid-phase principle in practice.', axAdd:{fat:1}},
      {mode:'Infused in liquid', note:'Water-soluble compounds only. A different, thinner extraction than fat gives.', axAdd:{}},
      {mode:'Dried',           note:'Volatiles diminish; the woody, resinous notes come forward.', axAdd:{}},
      {mode:'Charred / burnt',  note:'Smoke and bitterness enter. A different ingredient, really.', axAdd:{}}
    ],
    spice: [            // star anise, cinnamon, cardamom, pepper
      {mode:'Toasted whole',  note:'Heat drives Maillard in the spice itself — nuttier, rounder, less raw.', axAdd:{}},
      {mode:'Bloomed in fat', note:'Fat-soluble aromatics released and carried. The standard move, and it works for a reason.', axAdd:{fat:1}},
      {mode:'Ground raw',     note:'Sharpest and most volatile. Fades fastest.', axAdd:{}},
      {mode:'Steeped in liquid', note:'Slow, gentle extraction. Background rather than foreground.', axAdd:{}},
      {mode:'In a cure or rub', note:'Direct contact with the protein. Concentrated at the surface.', axAdd:{}}
    ],
    fruit: [            // cherry, plum, apple, quince
      {mode:'Fresh / raw',    note:'Acid, sweetness and juice, all intact.', axAdd:{}},
      {mode:'Pickled',        note:'Vinegar enters the fruit. Genuinely more acidic than it was.', axAdd:{acid:1}},
      {mode:'Reduced into a sauce', note:'Water leaves; sugars concentrate. Body and gloss arrive.', axAdd:{sweet:1}},
      {mode:'Roasted',        note:'Caramelisation. Sweetness deepens and acid softens.', axAdd:{sweet:1}},
      {mode:'Dried',          note:'Concentrated sweetness, and a chew.', axAdd:{sweet:1}}
    ],
    ferment: [          // miso, soy, fish sauce, fermented bean curd
      {mode:'Glaze',         note:'Painted on and caramelised. Sugars brown at the surface.', axAdd:{sweet:1}},
      {mode:'In a sauce',    note:'Dispersed. Savoury depth throughout rather than concentrated.', axAdd:{}},
      {mode:'Marinade / cure', note:'Salt and enzymes work into the protein over time. Texture changes, not just flavour.', axAdd:{}},
      {mode:'Whisked into fat', note:'Fat carries it; it becomes a finishing element rather than a base.', axAdd:{fat:1}},
      {mode:'In a broth',    note:'Diluted and dispersed — background savoury structure.', axAdd:{}}
    ],
    fungi: [            // porcini, shiitake, mushroom
      {mode:'Seared hard',   note:'Water leaves, Maillard arrives. Deeply savoury.', axAdd:{glut:1}},
      {mode:'Dried and rehydrated', note:'Drying concentrates the nucleotides sharply — a dried mushroom is far more umami-active than a fresh one.', axAdd:{glut:1, nucl:1}},
      {mode:'In a broth / dashi', note:'The guanylate extracts into the liquid. This is where the synergy lives.', axAdd:{nucl:1}},
      {mode:'Raw, shaved',   note:'Delicate, almost floral. Very little savoury depth.', axAdd:{}},
      {mode:'Confited in fat', note:'Silky, rich, saturated with the fat it cooked in.', axAdd:{fat:1}}
    ],
    starch: [           // potato, rice, bread, noodle, dumpling
      {mode:'Boiled / steamed', note:'Neutral, absorbent. A carrier for fat and sauce.', axAdd:{}},
      {mode:'Roasted / fried', note:'Surface Maillard; crisp exterior against a soft interior.', axAdd:{glut:1, fat:1}},
      {mode:'As a purée',     note:'Enriched with fat, smooth. Becomes a base rather than a component.', axAdd:{fat:1}},
      {mode:'Toasted',        note:'Nutty, dry, aromatic — a texture as much as a flavour.', axAdd:{}}
    ],
    dairy_fat: [        // butter, cream, coconut milk, oil
      {mode:'As a cooking medium', note:'Everything else passes through it. It carries the aromatics rather than adding its own.', axAdd:{}},
      {mode:'Emulsified into a sauce', note:'Body, gloss, and a carrier for fat-soluble aromatics.', axAdd:{}},
      {mode:'Browned',        note:'Milk solids Maillard — nutty, toasted, a genuinely different ingredient.', axAdd:{glut:1}},
      {mode:'Whipped / cold',  note:'Aeration and cold mute aroma. Season harder than seems right.', axAdd:{}},
      {mode:'Infused',        note:'The lipid phase captures aromatics and releases them slowly.', axAdd:{}}
    ],
    veg: [              // cucumber, cabbage, radish, zucchini
      {mode:'Raw',            note:'Crunch, water, freshness. A textural reset.', axAdd:{}},
      {mode:'Charred / grilled', note:'Water leaves, sugars caramelise, Maillard arrives.', axAdd:{sweet:1, glut:1}},
      {mode:'Pickled',        note:'Acid enters. Now it is a reset element, not just a texture.', axAdd:{acid:1}},
      {mode:'Roasted',        note:'Concentration and sweetness. The water goes.', axAdd:{sweet:1}},
      {mode:'As a purée',     note:'Smooth, enriched, a base rather than a component.', axAdd:{fat:1}}
    ]
  };

  /* Which class does an ingredient belong to? */
  const ING_CLASS = {
    'red wine':'liquid_alcohol','wine reduction':'liquid_alcohol','port':'liquid_alcohol','armagnac':'liquid_alcohol',
    'cider vinegar':'vinegar_acid','black vinegar':'vinegar_acid','wine vinegar':'vinegar_acid','verjus':'vinegar_acid','vinegar':'vinegar_acid','gastrique':'vinegar_acid',
    'scallion':'allium','shallot':'allium','garlic paste':'allium','roasted onion':'allium','black garlic':'allium','pickled shallot':'allium','chive oil':'allium','soffritto':'allium',
    'rosemary':'herb','thyme':'herb','sage':'herb','bay':'herb','juniper':'herb','spruce':'herb','fir':'herb','lavender':'herb','thai basil':'herb','marjoram':'herb','curry leaf':'herb','shiso':'herb','water spinach':'veg','mustard greens':'veg','kale':'veg',
    'star anise':'spice','cinnamon':'spice','cardamom':'spice','clove':'spice','pink peppercorn':'spice','caraway':'spice','sesame':'spice','cocoa':'spice','coffee':'spice','smoked paprika':'spice','ancho chile':'spice','pasilla chile':'spice','chile':'spice','ginger':'spice','galangal':'spice','horseradish':'spice','makrut lime leaf':'herb','makrut lime':'herb',
    'cherry':'fruit','tart cherry':'fruit','sour cherry':'fruit','plum':'fruit','apple':'fruit','quince':'fruit','pomegranate':'fruit','blood orange':'fruit','orange':'fruit','bitter orange':'fruit','grapefruit':'fruit','lychee':'fruit','pineapple':'fruit','grape':'fruit','apricot':'fruit','prune':'fruit','raisin':'fruit','tamarind':'fruit','green apple':'fruit','cranberry':'fruit','lingonberry':'fruit','tomato':'fruit','cherry tomato':'fruit','tomatillo':'fruit','lime':'fruit','sumac':'spice',
    'miso':'ferment','soy':'ferment','fish sauce':'ferment','fermented bean curd':'ferment','sweet bean sauce':'ferment','hoisin':'ferment','anchovy':'ferment','red curry paste':'ferment','rice ferment':'ferment','sauerkraut':'ferment','kimchi':'ferment','pickled cucumber':'veg','colatura':'ferment',
    'porcini':'fungi','shiitake':'fungi','mushroom':'fungi',
    'potato':'starch','rice':'starch','bread':'starch','dumpling':'starch','pancake':'starch','rice noodle':'starch','white bean':'starch','lentils':'starch','polenta':'starch','barley':'starch','toasted grain':'starch','taro':'starch','pappardelle':'starch','buckwheat':'starch','rye bread':'starch','chestnut':'starch',
    'coconut milk':'dairy_fat','coconut cream':'dairy_fat','parmesan':'ferment','pecorino':'ferment','aged cheese':'ferment','duck jus':'dairy_fat','stock':'dairy_fat','bone broth':'dairy_fat','pumpkin seed':'spice','almond':'spice','hazelnut':'spice','walnut':'spice','peanut':'spice','black olive':'ferment',
    'cucumber':'veg','radish':'veg','cabbage':'veg','red cabbage':'veg','fennel':'veg','celery':'veg','carrot':'veg','celeriac':'veg','zucchini':'veg','lettuce cup':'veg','crepe':'starch','sugar':'spice','honey':'spice','black tea':'spice','orange peel':'fruit','orange zest':'fruit','bergamot':'fruit','dried shrimp':'ferment','yeast extract':'ferment','sorrel':'herb','pickled walnut':'fruit','pomegranate molasses':'vinegar_acid','bacon':'ferment','coconut water':'dairy_fat','sweet potato':'veg','vanilla':'spice','pine nuts':'spice','basil':'herb','parsley':'herb','mint':'herb','capers':'ferment','olives':'ferment'
  };

  function modesFor(name){
    if (DELIVERY[name]) return DELIVERY[name];
    const cls = ING_CLASS[name];
    if (cls && CLASS_DELIVERY[cls]) return CLASS_DELIVERY[cls];
    return null;   // no invented modes. If we do not know, we say so.
  }

  let dish = [];
  let form = null;

  /* ============================================================
     CUISINE SCOPE — single-slot, exclusive, modeled on the `form`
     commit pattern (not the additive `dish[]` pattern). A scope is
     a mode the chef is working in, not a composed element of the dish.
     FLAG, NEVER FILTER: compound and co-occurrence lenses compute
     exactly the same whether or not a scope is locked. Only the
     Tradition lens has real per-thread region data in this demo —
     compound/co-occurrence chips are NOT given fabricated regional
     attestation, because this demo doesn't have real data for that,
     and inventing it would be exactly what this whole project exists
     to avoid. See the note both those lenses show when scope is locked.
     ============================================================ */
  const REGION_PICKS = [
    { key:'china',                          label:'China' },
    { key:'vietnam',                        label:'Vietnam' },
    { key:'thailand',                       label:'Thailand' },
    { key:'italy',                          label:'Italy' },
    { key:'france',                         label:'France' },
    { key:'mexico',                         label:'Mexico' },
    { key:'czech,poland,hungary,germany',   label:'Central Europe' }
  ];
  const REGION_ALIASES = {
    beijing:'china', sichuan:'china', tuscany:'italy', umbria:'italy',
    gascon:'france', gascony:'france', 'central europe':'czech,poland,hungary,germany'
  };

  let cuisineScope = null;   // { label, keys: [...] } or null — single active scope, exclusive

  function matchRegion(raw){
    const r = raw.toLowerCase().trim();
    const direct = REGION_PICKS.find(p => p.label.toLowerCase() === r || p.key.split(',').includes(r));
    if (direct) return { keys: direct.key.split(','), label: direct.label };
    const alias = REGION_ALIASES[r];
    if (alias){
      const p = REGION_PICKS.find(p => p.key === alias || p.key.split(',').includes(alias.split(',')[0]));
      if (p) return { keys: p.key.split(','), label: p.label };
    }
    return null;
  }

  function toggleScopeMenu(){
    document.getElementById('scope-menu').classList.toggle('open');
  }
  function closeScopeMenu(){
    document.getElementById('scope-menu').classList.remove('open');
  }

  function lockCuisine(key, label){
    const keys = key.split(',');
    if (cuisineScope && cuisineScope.keys.join(',') === keys.join(',')){
      clearCuisine();
      return;
    }
    cuisineScope = { label, keys };
    closeScopeMenu();
    renderScope();
    applyOverlays();
  }

  function clearCuisine(){
    cuisineScope = null;
    renderScope();
    applyOverlays();
  }

  function lockCuisineFromInput(){
    const inp = document.getElementById('scope-input');
    const raw = inp.value.trim();
    if (!raw) return;
    inp.value = '';
    closeScopeMenu();
    const match = matchRegion(raw);
    if (match) lockCuisine(match.keys.join(','), match.label);
    else showScopeDisambiguation(raw);
  }

  /* Honest disambiguation — no invented content. This is what a chef gets
     for a region with zero documented threads, e.g. "India" or "Malabar".
     Split so chat and the masthead menu can both reach it without either
     path double-posting the chef's own message. */
  function scopeDisambiguationReply(raw){
    const known = REGION_PICKS.map(p => p.label).join(', ');
    const h = '<p>No documented thread exists yet for <strong>' + raw + '</strong> \u2014 locking it would show you an empty result, or worse, a guessed one, and neither is honest.</p>' +
      '<p>What\'s actually documented right now: ' + known + '. If ' + raw + ' is close to one of these, say which \u2014 otherwise this stays open until a real thread is authored.</p>' +
      '<p class="ask">Lock one of the documented regions instead, or keep browsing without a scope?</p>';
    push('sys', h);
  }
  function showScopeDisambiguation(raw){
    lens('b', document.getElementById('tab-brain'));
    push('me', 'Cuisine scope: ' + raw);
    scopeDisambiguationReply(raw);
  }

  function renderScope(){
    const val = document.getElementById('scope-val');
    const btn = document.getElementById('scope-btn');
    const clearBtn = document.getElementById('scope-clear');
    const picks = document.getElementById('scope-picks');
    picks.innerHTML = REGION_PICKS.map(p =>
      '<button class="scope-pick" onclick="lockCuisine(\'' + p.key + '\',\'' + p.label + '\')">' + p.label + '</button>'
    ).join('');
    if (!cuisineScope){
      val.textContent = 'None';
      btn.classList.remove('locked');
      clearBtn.style.display = 'none';
      return;
    }
    val.textContent = cuisineScope.label;
    btn.classList.add('locked');
    clearBtn.style.display = 'inline';
  }

  /* Flag-not-filter, applied to the tradition pane's real region data.
     Called from within applyOverlays() so scope and form overlays stay
     in sync and never fight over the same DOM. */
  function applyCuisineOverlays(){
    document.querySelectorAll('.region-flag').forEach(n => n.remove());
    document.querySelectorAll('.scope-lens-note').forEach(n => n.remove());
    document.querySelectorAll('.group').forEach(g => g.classList.remove('region-match','region-nomatch'));

    if (!cuisineScope) return;

    // Tradition lens: real per-thread region data exists — flag honestly.
    document.querySelectorAll('#pane-t .group[data-region]').forEach(g => {
      const threadRegions = g.dataset.region.split(',');
      const isMatch = threadRegions.some(r => cuisineScope.keys.includes(r));
      const label = g.querySelector('.g-label');
      const flag = document.createElement('span');
      flag.className = 'region-flag ' + (isMatch ? 'match' : 'nomatch');
      flag.textContent = isMatch ? '\u2713 ' + cuisineScope.label : 'not ' + cuisineScope.label;
      label.appendChild(flag);
      g.classList.add(isMatch ? 'region-match' : 'region-nomatch');
    });

    // Compound + co-occurrence lenses: compute unfiltered, always. This demo
    // has no real per-ingredient region data for these lenses, so nothing
    // here is flagged attested or unattested — that would be fabrication.
    ['c','o'].forEach(k => {
      const pane = document.getElementById('pane-' + k);
      const intro = pane.querySelector('.pane-intro');
      const div = document.createElement('div');
      div.className = 'scope-lens-note';
      div.innerHTML = '<span class="sn-lbl">Cuisine scope: ' + cuisineScope.label + ' \u00b7 unfiltered</span>' +
        'This lens computes exactly the same with or without a locked scope \u2014 chemistry and corpus patterns aren\'t regional. ' +
        'Regional attestation only applies where it\'s actually documented, which in this demo is the Tradition lens.';
      intro.insertAdjacentElement('afterend', div);
    });
  }

  function commitForm(btn, name, desc){
    const same = (form && form.name === name);
    document.querySelectorAll('.commitf').forEach(b => {
      b.classList.remove('on');
      b.textContent = 'Commit this state';
    });
    if (same){ form = null; }
    else {
      form = { name, desc };
      btn.classList.add('on');
      btn.textContent = 'Committed ✓';
    }
    renderForm();
    applyOverlays();
    balance();
  }

  function clearForm(){
    form = null;
    document.querySelectorAll('.commitf').forEach(b => {
      b.classList.remove('on');
      b.textContent = 'Commit this state';
    });
    renderForm();
    applyOverlays();
    balance();
  }

  /* Chat-typed form/technique intent, same test as cuisine scope: form already
     has its own state variable (commitForm/FRAMES), independent of dish[]. */
  const FRAME_ALIASES = [
    { re:/\bcold[\s-]?salt/,               name:'Cold salted' },
    { re:/\bconfit/,                        name:'Confit' },
    { re:/\bbrais/,                         name:'Braise' },
    { re:/\bcrisp|roast/,                   name:'Crisp-skinned roast' },
    { re:/\bsear|magret/,                   name:'Seared magret' },
    { re:/\bcur(e|ed|ing)\b/,               name:'Cured' },
    { re:/\bbroth|soup/,                    name:'Broth system' },
    { re:/\bground|ragu|ragù|minced|sausage/, name:'Ground' },
    { re:/\bsmoke/,                         name:'Smoked' },
    { re:/\bterrine|rillette|pat[eé]/,      name:'Terrine / rillette' },
    { re:/\braw\b|tartare/,                 name:'Raw / tartare' }
  ];
  function matchFrame(raw){
    for (const a of FRAME_ALIASES) if (a.re.test(raw)) return a.name;
    return null;
  }
  function lockFormFromChat(name){
    // Reuse the real commit button rather than duplicating commitForm()'s
    // logic — this is the same state change a click would produce.
    const btn = document.querySelector('.commitf[onclick*="\'' + name + '\'"]');
    if (btn) btn.click();
    const fTab = document.querySelector('.tab-f');
    if (fTab) lens('f', fTab);
  }

  function renderForm(){
    const sec = document.getElementById('form-sec');
    const show = document.getElementById('form-show');
    if (!form){ sec.style.display = 'none'; show.innerHTML = ''; return; }
    sec.style.display = 'block';
    show.innerHTML = '<div class="fcard"><div class="fn">' + form.name +
                     '</div><div class="fd">' + form.desc + '</div></div>';
  }

  /* ---- DERIVED, not authored. Compare thread.requires vs frame.absent ---- */
  function tensionFor(requires){
    if (!form) return null;
    const f = FRAMES[form.name];
    if (!f) return null;
    const clash = requires.filter(r => f.absent.indexOf(r) !== -1);
    if (!clash.length) return null;
    return {
      missing: clash.map(c => PROP_LABELS[c] || c),
      gives: f.produces.slice(0,3).map(c => PROP_LABELS[c] || c)
    };
  }

  function applyOverlays(){
    applyCuisineOverlays();

    // behaviour overlay — one per frame, inherited by every ingredient field
    document.querySelectorAll('.overlay-note').forEach(n => n.remove());
    document.querySelectorAll('.tension').forEach(n => n.remove());
    if (!form) return;

    const f = FRAMES[form.name];
    const ov = OVERLAYS[f.overlay];

    // one behaviour note at the top of each lens pane
    ['c','t','o'].forEach(k => {
      const pane = document.getElementById('pane-' + k);
      const intro = pane.querySelector('.pane-intro') || pane.firstElementChild;
      const div = document.createElement('div');
      div.className = 'overlay-note';
      div.innerHTML = '<span class="on-lbl">In a ' + form.name.toLowerCase() +
                      ' frame · behaviour shift</span>' + ov +
                      '<span class="on-foot">Nothing is hidden or reordered. The options are the same — what they <em>do</em> is different.</span>';
      intro.insertAdjacentElement('afterend', div);
    });

    // tension notices — derived per thread, only where a real clash exists
    document.querySelectorAll('[data-requires]').forEach(btn => {
      const t = tensionFor(btn.dataset.requires.split(','));
      if (!t) return;
      const group = btn.closest('.group');
      const div = document.createElement('div');
      div.className = 'tension';
      div.innerHTML =
        '<span class="t-lbl">Tension to notice · derived</span>' +
        '<p>You\'ve committed to <strong>' + form.name.toLowerCase() + '</strong> and this is ' +
        btn.dataset.thread + ', which assumes <strong>' + t.missing.join(' and ') +
        '</strong>. Your frame gives you ' + t.gives.join(', ') + ' instead.</p>' +
        '<p class="t-q">That does not make the path wrong — it changes the design question. Restore what\'s missing, or let the frame you chose do the work?</p>';
      group.appendChild(div);
    });
  }

  function add(el, name, lens){
    if (dish.find(d => d.name === name)) return;
    // An ingredient enters WITHOUT a form. It is a candidate, not yet part of the dish.
    dish.push({name, lens, mode:null, modeNote:null, axAdd:null});
    el.classList.add('added');
    el.querySelector('.plus').textContent = '\u2713';
    render();
    applyOverlays();
  }

  /* ---- COMPOSITION: give an ingredient a form, or several ----
     The same ingredient can be committed in MULTIPLE modes — charred scallion oil
     beneath, raw scallion on top. That is composition, and it is how chefs actually
     build dishes. The dish is a list of (ingredient, delivery) pairs. */
  let openIdx = null;
  function openModes(i){
    openIdx = (openIdx === i) ? null : i;
    render();
  }
  function setMode(i, mi){
    const d = dish[i];
    const modes = modesFor(d.name);
    if (!modes) return;
    const m = modes[mi];
    d.mode = m.mode; d.modeNote = m.note; d.axAdd = m.axAdd;
    openIdx = null;
    render();
    balance();
  }
  function duplicateIn(i){
    // commit the same ingredient again, in a different mode
    const d = dish[i];
    dish.push({name:d.name, lens:d.lens, mode:null, modeNote:null, axAdd:null});
    openIdx = dish.length - 1;
    render();
  }

  function remove(name){
    dish = dish.filter(d => d.name !== name);
    document.querySelectorAll('.chip').forEach(c => {
      const label = c.textContent.trim().replace(/^[+\u2713]\s*/, '');
      if (label === name) {
        c.classList.remove('added');
        c.querySelector('.plus').textContent = '+';
      }
    });
    render();
    applyOverlays();
  }

  function render(){
    const list = document.getElementById('dish-list');
    const formed = dish.filter(d => d.mode);
    document.getElementById('count').textContent = formed.length + '/' + dish.length;

    if (!dish.length){
      list.innerHTML = '<div class="dish-empty">Nothing gathered yet. Add ingredients from the right — then give each one a form.</div>';
      renderPhase();
      return;
    }

    list.innerHTML = dish.map((d, i) => {
      const modes = modesFor(d.name);
      const open = (openIdx === i);
      let html = '<div class="ing' + (d.mode ? ' formed' : ' unformed') + '" style="--src:' + COLORS[d.lens] + '">';
      html += '<div class="ing-top">';
      html += '<span class="ing-n">' + d.name + (d.mode ? ' <span class="ing-m">' + d.mode.toLowerCase() + '</span>' : '') + '</span>';
      html += '<span class="ing-btns">';
      if (d.mode) html += '<button class="mini" onclick="duplicateIn(' + i + ')" title="Use again in another form">+form</button>';
      if (!modes && !d.mode) html += '<span class="nomode-tag">no modes yet</span>';
      html += '<button class="mini" onclick="openModes(' + i + ')">' + (d.mode ? 'change' : 'give it a form') + '</button>';
      html += '<button class="mini x" onclick="removeAt(' + i + ')">\u00d7</button>';
      html += '</span></div>';
      if (d.mode && d.modeNote) html += '<div class="ing-note">' + d.modeNote + '</div>';
      if (open){
        html += '<div class="modes">';
        if (!modes){
          html += '<div class="no-modes">We have not authored delivery modes for this ingredient yet. Rather than invent them, the system says so.</div>';
        }
        (modes || []).forEach((m, mi) => {
          html += '<button class="mode-b" onclick="setMode(' + i + ',' + mi + ')">' +
                  '<span class="mode-n">' + m.mode + '</span>' +
                  '<span class="mode-w">' + m.note + '</span></button>';
        });
        html += '</div>';
      }
      html += '</div>';
      return html;
    }).join('');
    renderPhase();
    const b = document.getElementById('brain-badge');
    if (b) b.textContent = dish.length ? dish.length : '';
    if (chat.length === 0) renderChat();
  }

  function removeAt(i){
    const name = dish[i].name;
    dish.splice(i,1);
    if (!dish.find(d => d.name === name)){
      document.querySelectorAll('.chip').forEach(c => {
        const label = c.textContent.trim().replace(/^[+\u2713]\s*/, '');
        if (label === name){ c.classList.remove('added'); c.querySelector('.plus').textContent = '+'; }
      });
    }
    openIdx = null;
    render(); applyOverlays(); balance();
  }

  /* ---- PHASE: search vs composition ----
     During SEARCH the chef is gathering possibilities — there is no dish to balance yet.
     COMPOSITION begins when ingredients start getting forms. The dish is "done" when
     every ingredient has one — not because the system decides, but because an ingredient
     without a form is not in the dish, it is on a list. */
  function renderPhase(){
    const el = document.getElementById('phase');
    if (!el) return;
    const formed = dish.filter(d => d.mode).length;
    const total = dish.length;
    if (!total){
      el.className = 'phase search';
      el.innerHTML = '<span class="ph-l">Gathering</span>Pull ingredients from the lenses. Give them forms whenever you are ready \u2014 or not at all.';
    } else if (formed < total){
      el.className = 'phase compose';
      el.innerHTML = '<span class="ph-l">Composing</span>' + formed + ' of ' + total + ' have a form. An ingredient can appear more than once \u2014 charred beneath, raw on top.';
    } else {
      el.className = 'phase done';
      el.innerHTML = '<span class="ph-l">Every element has a form</span>Nothing here says the dish is finished. That is your call.';
    }
  }

  function balance(){
    // Start from the anchor itself. Duck is not a blank slate with a fat number —
    // it is a red meat carrying inosinate, savoury depth and (once seared) Maillard.
    const base = form && FRAMES[form.name] ? FRAMES[form.name].fat : 0.6;
    const t = {glut: ANCHOR.glut, nucl: ANCHOR.nucl, salt:0, fat:base, acid:0, sweet:0,
               capsaicin:0, pungent:0, trigeminal:0};
    if (form && FRAMES[form.name].produces.indexOf('salt-cured') !== -1) t.salt += 1;

    /* Every committed ingredient counts. Most contribute the same whatever you do with
       them — curry paste is capsaicin, salt and glutamate as a rub or as a sauce; the
       delivery changes intensity and placement, not composition.
       Delivery MODIFIES the contribution only where it genuinely alters the chemistry:
       char produces Maillard compounds that were not there; pickling adds acid;
       reduction concentrates sugar. Those are real changes. Intensity is not. */
    dish.forEach(d => {
      const base = AXES[d.name] || {};
      for (const k in base) if (k in t) t[k] += base[k];
      // delivery adds only what the transformation actually creates
      const add = d.axAdd || {};
      for (const k in add) if (k in t) t[k] += add[k];
    });
    const n = dish.length + 1;
    const msg = document.getElementById('bal-msg');

    /* ---------- UMAMI: one axis, synergy shown as STATE not as a second bar ----------
       Umami is ONE sensation with two interacting inputs. Glutamate + nucleotide is
       ~8x glutamate alone. The useful information is not the level — it's whether
       the synergy is unlocked. So: solid fill = what you have; hatched ghost = the
       amplification sitting unclaimed. */
    const umamiHave = t.glut > 0 ? (t.glut / n) : 0;
    const synergyOn = t.glut > 0 && t.nucl > 0;
    const umAxis = document.querySelector('.axis[data-axis="umami"]');
    const umFill = umAxis.querySelector('.fill');
    const syn    = document.getElementById('syn-mark');
    const umLbl  = document.getElementById('an-umami');

    if (synergyOn) {
      umFill.style.width = Math.min(100, umamiHave * 100 * 2.2) + '%';
      syn.classList.remove('show');
      umLbl.textContent = 'Umami ×';
      umLbl.classList.add('resolved');
    } else {
      umFill.style.width = Math.min(100, umamiHave * 100) + '%';
      umLbl.textContent = 'Umami';
      umLbl.classList.remove('resolved');
      if (t.glut > 0) {
        // ghost: the amplification available but not taken
        syn.classList.add('show');
        syn.style.left  = Math.min(100, umamiHave * 100) + '%';
        syn.style.width = Math.min(100 - umamiHave*100, umamiHave * 100 * 1.2) + '%';
      } else {
        syn.classList.remove('show');
      }
    }

    /* ---------- HEAT: one axis that RESOLVES to its mechanism when one is committed ----------
       Capsaicin, isothiocyanates and sanshool are not the same sensation. But three
       permanent bars is dead space on a dish that touches none of them. So the axis
       names itself only when it becomes real. */
    const heatAxis = document.querySelector('.axis[data-axis="heat"]');
    const heatLbl  = document.getElementById('an-heat');
    const mechs = [
      {k:'capsaicin',  label:'Capsaicin',  v:t.capsaicin},
      {k:'pungent',    label:'Volatile',   v:t.pungent},
      {k:'trigeminal', label:'Tingling',   v:t.trigeminal}
    ].filter(m => m.v > 0);

    let heatTotal = 0, heatNote = null;
    if (mechs.length === 0) {
      heatLbl.textContent = 'Heat';
      heatLbl.classList.remove('resolved');
    } else if (mechs.length === 1) {
      const m = mechs[0];
      heatTotal = m.v;
      heatLbl.textContent = m.label;
      heatLbl.classList.add('resolved');
      if (m.k === 'capsaicin')  heatNote = {ax:'heat', note:'Capsaicin is lipophilic — fat and dairy genuinely mute it. This is the one pungency where that works.'};
      if (m.k === 'pungent')    heatNote = {ax:'heat', note:'Volatile pungency — isothiocyanates, from wasabi, horseradish or mustard. Nasal rather than oral, and it dissipates. Fat does essentially nothing here; it simply leaves.'};
      if (m.k === 'trigeminal') heatNote = {ax:'heat', note:'This is trigeminal, not heat. Sanshool tingles and numbs; ginger warms. It is not burning, and balancing it with fat would do nothing — there is nothing to cut.'};
    } else {
      heatTotal = mechs.reduce((a,m) => a + m.v, 0);
      heatLbl.textContent = mechs.map(m => m.label).join(' + ');
      heatLbl.classList.add('resolved');
      heatNote = {ax:'heat', note:'Two different pungency mechanisms are in play — ' + mechs.map(m=>m.label.toLowerCase()).join(' and ') + '. They do not compound with each other and they do not respond to the same correction. Fat mutes capsaicin only.'};
    }
    heatAxis.querySelector('.fill').style.width = Math.min(100, (heatTotal/n) * 100) + '%';

    /* ---------- the remaining axes ---------- */
    [['salt',t.salt],['fat',t.fat],['acid',t.acid],['sweet',t.sweet]].forEach(([k,v]) => {
      const ax = document.querySelector('.axis[data-axis="'+k+'"]');
      if (ax) ax.querySelector('.fill').style.width = Math.min(100, (v/n)*100) + '%';
    });
    document.querySelectorAll('.axis').forEach(a => a.classList.remove('flagged'));

    if (dish.length < 3){
      msg.className = 'bal-gate';
      msg.textContent = 'Balance check begins at 3 ingredients. (' + dish.length + '/3)';
      return;
    }

    const flags = [];

    // umami synergy — the state, not the level
    const addedGlut = t.glut - ANCHOR.glut;
    if (addedGlut > 0) {
      flags.push({ax:'umami', note:'The duck already brings a nucleotide — it is a red meat, and inosinate rises further with searing and ageing. So a glutamate ingredient added to duck is not accumulating umami, it is amplifying it: glutamate plus nucleotide is roughly an order of magnitude, not a sum. This is the dashi principle, and the duck is doing what the bonito does.'});
    } else if (t.nucl > 0 && addedGlut === 0) {
      flags.push({ax:'umami', note:'Duck carries inosinate but little free glutamate. The hatched bar is the amplification sitting unclaimed — a glutamate source (miso, soy, aged cheese, tomato, kombu) multiplies the savoury depth far beyond what another meaty ingredient would.'});
    }

    if (heatNote) flags.push(heatNote);

    // acid <-> sweet: bidirectional mutual suppression (Brix/acid ratio, 7 CFR 93.2)
    if (t.acid / n >= 0.4 && t.sweet < t.acid) {
      flags.push({ax:'acid', note:'Trending acidic with little to offset it. Sugars suppress perceived tartness and acids suppress perceived sweetness — a documented mutual suppression. Or reach for a drying, tannic reset instead.'});
    }

    // salt <-> fat: holds, but ASYMMETRICALLY
    if (t.salt / n >= 0.45) {
      flags.push({ax:'salt', note:'Salt building. Fat suppresses perceived saltiness — only free sodium ions reach the receptor, and fat impedes their release from the matrix. Note this runs one way only.'});
    }
    if (t.fat / n >= 0.55 && t.acid === 0) {
      flags.push({ax:'fat', note:'Rich, with no reset committed. Sourness brightens; astringency dries — different mechanisms, so which do you want? Salt will not cut this; that pair only runs the other way.'});
    }

    if (!flags.length){
      msg.className = 'bal-gate';
      msg.textContent = 'Nothing trending. Keep building.';
    } else {
      const f = flags[0];
      const el = document.querySelector('.axis[data-axis="' + f.ax + '"]');
      if (el) el.classList.add('flagged');
      msg.className = 'bal-note';
      msg.textContent = f.note;
    }
  }


  /* ============================================================
     BRAINSTORM — the composition conversation.
     THE LINE: the system never chooses the ingredients. The chef did that,
     and that was the creative act. Once a set exists, suggesting ARRANGEMENTS
     of that set is craft assistance, not authorship — the same thing a sous
     chef does. Suggestions come BY REQUEST, and always PLURAL and EXPLAINED,
     because a single answer ends the thinking and the product's job is to
     extend it.
     ============================================================ */
  let chat = [];

  const FUNCTION_OF = {
    ferment:'savoury depth', fungi:'savoury depth', allium:'aromatic base',
    herb:'aromatic lift', spice:'aromatic lift', fruit:'acid and sweetness',
    vinegar_acid:'acid', liquid_alcohol:'acid and body', starch:'a carrier for the fat',
    dairy_fat:'fat and body', veg:'freshness and crunch'
  };
  /* Which job a DELIVERY-created axis contribution counts toward, when it
     differs from the ingredient's static class. Deliberately narrow — only
     the axes that feed a real observations() check (acid → the "reset" check;
     sweet → the same; fat → richness/body). Not every axis needs a job. */
  const AXADD_JOB = { acid:'acid', sweet:'acid and sweetness', fat:'fat and body' };

  function dishRead(){
    const t = {glut:ANCHOR.glut, nucl:ANCHOR.nucl, salt:0, fat:0.6, acid:0, sweet:0,
               capsaicin:0, pungent:0, trigeminal:0};
    dish.forEach(d => {
      const b = AXES[d.name] || {};
      for (const k in b) if (k in t) t[k] += b[k];
      const a = d.axAdd || {};
      for (const k in a) if (k in t) t[k] += a[k];
    });
    const jobs = {};
    const addJob = (f, name) => { if (!f) return; (jobs[f] = jobs[f] || []).push(name); };
    dish.forEach(d => {
      const staticJob = FUNCTION_OF[ING_CLASS[d.name]] || 'other';
      addJob(staticJob, d.name);
      /* BUG FIX: delivery can create a real functional contribution the static
         class doesn't reflect — orange peel in a gastrique genuinely becomes
         acidic, which its base 'aromatic lift' class says nothing about. Without
         this, the numeric balance (t, above) counts the acid correctly while
         observations() below still says "there is no reset" for the same
         ingredient in the same dish. Count what delivery actually created,
         in addition to the static class — never instead of it. */
      const add = d.axAdd || {};
      Object.keys(add).forEach(axis => {
        const derivedJob = AXADD_JOB[axis];
        if (derivedJob && derivedJob !== staticJob && !(jobs[derivedJob]||[]).includes(d.name)){
          addJob(derivedJob, d.name);
        }
      });
    });
    return {t, jobs};
  }

  /* --- OBSERVATIONS: what the system notices. Never a recommendation. --- */
  function observations(){
    const {t, jobs} = dishRead();
    const o = [];
    const names = dish.map(d => d.name);

    if (t.glut > ANCHOR.glut && t.nucl > ANCHOR.nucl)
      o.push('You have glutamate and nucleotide sources both in play, and the duck brings a nucleotide of its own. The savoury depth here is multiplying, not adding — that is a big lever, and it is already pulled.');
    else if (t.glut > ANCHOR.glut && t.nucl === ANCHOR.nucl)
      o.push('The duck already carries a nucleotide, so the glutamate you have added is amplifying rather than accumulating. A dried mushroom or an aged cheese would push that further — but you may already be where you want to be.');

    if (!jobs['a carrier for the fat'])
      o.push('Nothing here catches the rendered fat. That is a real choice, not an omission — but it is worth making on purpose. A starch, a bread, a bean, a purée.');
    if (!jobs['acid'] && !jobs['acid and sweetness'] && !jobs['acid and body'])
      o.push('There is no reset. Duck is rich and it accumulates — something sour, tart, or drying gives the palate somewhere to go between bites.');
    if (!jobs['freshness and crunch'])
      o.push('No textural contrast. Everything here is soft or rendered. Worth asking whether you want something raw against it.');

    const aromatics = (jobs['aromatic lift'] || []).length;
    if (aromatics >= 3)
      o.push('You have ' + aromatics + ' aromatics — ' + (jobs['aromatic lift']||[]).join(', ') + '. They are competing for the same channel rather than layering. That can be deliberate, but three is a lot of voices in one register.');

    if (t.capsaicin > 0 && t.acid === 0 && !names.includes('coconut milk'))
      o.push('There is heat with nothing fat or sweet to carry it. Capsaicin is lipophilic — it needs fat to spread, or it just sits and burns in one place.');

    const unformed = dish.filter(d => !d.mode);
    if (unformed.length && dish.length > 2)
      o.push('Still undecided: ' + unformed.map(d=>d.name).join(', ') + '. Where each one sits will change the dish more than which one it is.');

    return o;
  }

  /* --- DIRECTIONS: plural, explained, non-ranked. Only on request. --- */
  function directions(){
    const {jobs} = dishRead();
    const names = dish.map(d => d.name);
    const has = n => names.includes(n);
    const D = [];

    if (dish.length < 3){
      return null;   // not enough of a set to arrange. Push back instead.
    }

    // Direction 1 — hold the duck as the centrepiece; everything serves it
    D.push({
      t:'The duck stays the plate',
      b:'Seared breast, rested, sliced. The aromatics work at the surface where the fat renders — a rub that hits the sear, or an oil brushed on at the end. Everything else sits beside it as discrete elements rather than dissolving into a sauce. The tension you get is between the crisp fat cap and whatever is sharp on the plate.',
      w:'This asks the least of the other ingredients and the most of your cooking. The duck has nowhere to hide.'
    });

    // Direction 2 — dissolve the duck into a system
    D.push({
      t:'The duck disappears into a system',
      b:'Broth, braise, or sauce. The richness leaves the plate and becomes structure — everything you have gathered goes into a liquid and the duck is a base rather than a slice. ' + (has('red curry paste') ? 'The curry paste is built for this: bloomed in fat, thinned, it carries everything.' : 'The savoury elements have far more room here than on a plate.'),
      w:'The opposite trade. Forgiving to cook, harder to make feel like a composed dish rather than a bowl.'
    });

    // Direction 3 — echo one ingredient across states
    const echoable = dish.find(d => ['allium','herb','fruit','veg'].includes(ING_CLASS[d.name]));
    if (echoable){
      D.push({
        t:'One ingredient, three registers',
        b:'Take ' + echoable.name + ' and use it in more than one state. Charred beneath, raw on top, and something in between — an oil, a pickle, a purée. The same element appearing in different registers is what separates a composed dish from a plate of ingredients.',
        w:'This is a compositional device, not a flavour one. It can also read as a gimmick if the states are not doing different jobs.'
      });
    }

    // Direction 4 — invert what is serving what
    if (jobs['savoury depth'] && jobs['savoury depth'].length){
      D.push({
        t:'Let the sauce be the dish',
        b:'Mole logic. The duck becomes the vehicle and ' + jobs['savoury depth'][0] + ' — with whatever else you have — becomes the point. Seeds, nuts, or reduction supply the body instead of fat. The protein serves the sauce rather than the other way round.',
        w:'An inversion of European roast logic. It changes the whole texture of the plate, and it demands a lot of the sauce.'
      });
    }

    return D;
  }

  function push(who, html){ chat.push({who, html}); renderChat(); }

  function renderChat(){
    const box = document.getElementById('chatlog');
    if (!box) return;
    if (!chat.length){
      const n = dish.length;
      box.innerHTML = '<div class="chat-empty">' +
        (n === 0
          ? 'Gather a few ingredients first. The system will never choose them for you \u2014 that part is yours.'
          : 'You have ' + n + ' ingredient' + (n>1?'s':'') + '. Ask what to do with them, or just think out loud.') +
        '</div>';
    } else {
      box.innerHTML = chat.map(c =>
        '<div class="msg ' + c.who + '">' +
        (c.who==='sys' ? '<span class="msg-l">CulinAI</span>' : '') + c.html + '</div>'
      ).join('');
      box.scrollTop = box.scrollHeight;
    }
    renderQuick();
  }

  function renderQuick(){
    const q = document.getElementById('quick');
    if (!q) return;
    const opts = ['What do you notice?', 'Suggest some directions', "What's missing?", 'Write the dish up'];
    q.innerHTML = opts.map(o => '<button class="qb" onclick="sendChat(\'' + o + '\')">' + o + '</button>').join('');
  }

  function sendChat(preset){
    const box = document.getElementById('chatbox');
    const txt = (preset || (box ? box.value : '')).trim();
    if (!txt) return;
    if (box) box.value = '';
    push('me', txt);
    setTimeout(() => respond(txt.toLowerCase()), 320);
  }

  function respond(q){
    // Cuisine scope can be set from chat too, independent of dish state —
    // both entry points (this, and the masthead lock menu) route through
    // the same lockCuisine()/scopeDisambiguationReply() so behavior matches.
    const scopeCmd = q.match(/^(?:lock|cuisine scope|scope)\s*(?:to|:)?\s+(.+)/);
    if (scopeCmd){
      const raw = scopeCmd[1].trim();
      const match = matchRegion(raw);
      if (match){
        lockCuisine(match.keys.join(','), match.label);
        push('sys', '<p>Locked to <strong>' + match.label + '</strong>. Tradition threads are flagged accordingly — nothing is hidden, and compound and co-occurrence stay fully unfiltered.</p>');
      } else {
        scopeDisambiguationReply(raw);
      }
      return;
    }

    /* Form/technique carved out the same way, on the same test: does this intent
       have its own state variable, independent of dish composition? `form` does
       — it's the same commitForm()/FRAMES mechanism the Form tab already uses.
       Deliberately NOT extended to event-scale or other intent types that have
       no real state to land in yet — see the dev notes for why that's a
       different call, not an oversight. */
    const frameMatch = matchFrame(q);
    if (frameMatch && dish.length === 0){
      lockFormFromChat(frameMatch);
      push('sys', '<p>Set the form to <strong>' + frameMatch + '</strong> — you can see it under the Form tab, and change your mind any time by clicking it again. Ingredients still gather however you like; this just answers "what state of duck," not "what\'s in it."</p>');
      return;
    }

    if (dish.length === 0){
      push('sys','<p>Nothing gathered yet — and I won\'t pick for you. Choosing the ingredients is the creative act, and it\'s yours. Work through the lenses, pull what interests you, and then we can talk about what to do with it.</p>');
      return;
    }

    // "suggest something" / directions
    if (/suggest|direction|idea|what could|options|not sure|help me/.test(q)){
      const D = directions();
      if (!D){
        push('sys','<p>You have ' + dish.length + ' ingredient' + (dish.length>1?'s':'') + '. That\'s not really a set yet — anything I suggested would be me designing the dish, not arranging yours.</p><p>Pull a few more and the arrangement question gets real.</p>');
        return;
      }
      let h = '<p>Here are ' + D.length + ' directions. They are genuinely different dishes, not variations — and I\'m not ranking them.</p>';
      D.forEach(d => {
        h += '<div class="dir"><div class="dir-t">' + d.t + '</div><div class="dir-b">' + d.b +
             '</div><div class="dir-w">' + d.w + '</div></div>';
      });
      h += '<p class="ask">Which of these is closest to what you\'re seeing?</p>';
      push('sys', h);
      return;
    }

    // "what's missing"
    if (/missing|lacking|need|gap|absent/.test(q)){
      const o = observations().filter(x => /Nothing here catches|There is no reset|No textural/.test(x));
      if (!o.length){ push('sys','<p>Nothing structural is missing — you have savoury depth, a reset, and a carrier. What\'s left is arrangement, not addition.</p>'); return; }
      push('sys','<p>' + o.join('</p><p>') + '</p><p class="ask">None of these is a problem unless you think it is.</p>');
      return;
    }

    // write it up
    if (/write|recipe|outline|summar|describe|done|finish/.test(q)){
      writeUp();
      return;
    }

    // default: observe
    const o = observations();
    if (!o.length){
      push('sys','<p>Nothing is jumping out. Tell me what you\'re trying to make it feel like and I\'ll tell you what\'s in the way.</p>');
      return;
    }
    push('sys','<p>' + o.slice(0,3).join('</p><p>') + '</p><p class="ask">Any of that useful, or are you working toward something specific?</p>');
  }

  /* --- THE ENDPOINT. The machine writes down what the CHEF designed. --- */
  function writeUp(){
    const {jobs} = dishRead();
    const formed = dish.filter(d => d.mode);
    const unformed = dish.filter(d => !d.mode);

    let h = '<div class="writeup"><div class="wu-h">The dish, as you have built it</div>';
    h += '<p class="wu-lead">Duck breast' + (form ? ', ' + form.name.toLowerCase() : '') + '.</p>';

    if (formed.length){
      h += '<div class="wu-s">Elements</div><ul>';
      formed.forEach(d => h += '<li><strong>' + d.name + '</strong> — ' + d.mode.toLowerCase() + '</li>');
      h += '</ul>';
    }
    if (unformed.length){
      h += '<div class="wu-s">Still without a form</div><p class="wu-note">' +
           unformed.map(d=>d.name).join(', ') + ' — these are gathered but not placed. The write-up can\'t be complete until they are, or until you drop them.</p>';
    }

    h += '<div class="wu-s">What it does</div><ul>';
    Object.entries(jobs).forEach(([job, ings]) => {
      h += '<li><strong>' + job + '</strong>: ' + ings.join(', ') + '</li>';
    });
    h += '</ul>';

    const o = observations();
    if (o.length){
      h += '<div class="wu-s">Unresolved</div><ul>';
      o.slice(0,3).forEach(x => h += '<li>' + x + '</li>');
      h += '</ul>';
    }

    h += '<div class="wu-foot">This is a description of what you designed, not a recipe. Say <em>"draft the method"</em> and I\'ll write the sequence and quantities for you to check — that part is wordsmithing, and it\'s the only thing here I should be doing.</div></div>';
    push('sys', h);
  }

  function lens(k, btn){
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('on'));
    btn.classList.add('on');
    document.querySelectorAll('.pane').forEach(p => p.classList.remove('on'));
    document.getElementById('pane-' + k).classList.add('on');
  }

  function why(id, btn){
    const b = document.getElementById(id);
    b.classList.toggle('open');
    btn.textContent = b.classList.contains('open')
      ? btn.textContent.replace('→','↑')
      : btn.textContent.replace('↑','→');
  }

  document.addEventListener('click', (e) => {
    const ctrl = document.querySelector('.scope-control');
    if (ctrl && !ctrl.contains(e.target)) closeScopeMenu();
  });

  /* Scoped deliberately to the ~5 ingredients with real DELIVERY entries —
     not every ingredient that could theoretically vary by form. Flagging
     everything would be exactly the cluttered-UI outcome to avoid; this only
     marks the cases where the demo actually has different behavior on file. */
  const FORM_DEPENDENT = new Set(Object.keys(DELIVERY));
  function flagFormDependentChips(){
    document.querySelectorAll('.chip').forEach(chip => {
      const oc = chip.getAttribute('onclick') || '';
      const m = oc.match(/add\(this,'([^']+)'/);
      if (m && FORM_DEPENDENT.has(m[1])){
        chip.classList.add('form-dependent');
        chip.title = 'Function depends on how you use it — see Delivery modes once added.';
      }
    });
  }


/* --- expose inline-handler functions to window (inline onclick=... needs globals) --- */
Object.assign(window, {
  add,
  applyCuisineOverlays,
  applyOverlays,
  balance,
  clearCuisine,
  clearForm,
  closeScopeMenu,
  commitForm,
  directions,
  dishRead,
  duplicateIn,
  flagFormDependentChips,
  lens,
  lockCuisine,
  lockCuisineFromInput,
  lockFormFromChat,
  matchFrame,
  matchRegion,
  modesFor,
  observations,
  openModes,
  push,
  remove,
  removeAt,
  render,
  renderChat,
  renderForm,
  renderPhase,
  renderQuick,
  renderScope,
  respond,
  scopeDisambiguationReply,
  sendChat,
  setMode,
  showScopeDisambiguation,
  tensionFor,
  toggleScopeMenu,
  why,
  writeUp
});

/* React drives this after the markup is mounted (see App.jsx). */
export function init() {
  renderScope();
  flagFormDependentChips();
  render();
}
