from __future__ import annotations

# Simple dictionary tags — enrichment for the dietary-filter step later.
ALLERGENS: dict[str, set[str]] = {
    "butter": {"dairy"},
    "flour": {"gluten"},
    "chicken": {"meat"},
    "duck": {"meat"},
    "short ribs": {"meat"},
    "garlic": set(),
}

DIET_BLOCKS: dict[str, set[str]] = {
    # diet_name → ingredients that violate it
    "vegan": {"butter", "chicken", "duck", "short ribs"},
    "vegetarian": {"chicken", "duck", "short ribs"},
    "gluten_free": {"flour"},
}


def tag_recipe(ingredients: list[str]) -> dict:
    allergens: set[str] = set()
    for ing in ingredients:
        allergens |= ALLERGENS.get(ing, set())
    diets = []
    for diet, blockers in DIET_BLOCKS.items():
        if not set(ingredients) & blockers:
            diets.append(diet)
    return {"allergens": sorted(allergens), "diet_ok": sorted(diets)}
