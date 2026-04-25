You are given a JSON input that was extracted by AI and may contain imperfect
grouping or structure. You may restructure and correct the input as
needed, following the rules below, in order to produce the best possible target
JSON.

The input contains:

1. exactly one category entry with `category_role = "normal_category"`
2. zero or more related shared sections with category roles from:
   - `shared_sizes_section`
   - `shared_options_section`
   - `shared_toppings_section`
   - `shared_modifiers_section`
   - `mixed_shared_section`

Your job is to merge the information from this subset into a single JSON object
matching the target `category_item_minimal.schema.json` format.

Core task:

- Treat the single `normal_category` as the target category.
- Use the shared sections only to augment the target category when they apply to
  it.
- Produce one flattened category payload in the target schema shape.

Important rules:

1. Return JSON only.
2. Do not include markdown fences.
3. Do not invent information.
4. Do not include free-text category or item descriptions in the final output.
5. Use descriptions and modifiables as supporting evidence to derive
   structured sizes, options, toppings, prices, and rules when the information
   is stated clearly enough.
6. If a shared section applies to the target category, fold that information
   into the target category output instead of preserving the shared section as a
   separate object.
7. If multiple shared sections contribute relevant information, merge them.
8. Use the target category as the scope anchor for all decisions.
9. Capture all important prices, sizes, options, toppings, and item-specific
   rules that can be structured from the input subset.
10. When in doubt, prefer preserving information in the closest valid target
    field rather than dropping it.

Mapping guidance:

- `category_description`:
  - do not populate this field
- `category_sizes`:
  - populate from shared size sections or category-level size information that
    applies to the target category
- `category_options`:
  - populate from shared option/modifier sections or category-level options that
    apply to the target category
  - infer options from both modifiables and descriptions
  - if explicit min/max are not stated, default to `minRequired=0` and
    `maxAllowed=2`
  - if the option is essential to complete the order, use
    `minRequired=1, maxAllowed=1`
- `category_toppings`:
  - populate from shared topping sections or category-level topping information
    that applies to the target category
  - infer toppings from both modifiables and descriptions
- `items`:
  - create item entries from the target category's item list
  - enrich each item with item-level prices, sizes, options, and
    toppings that can be derived from the target category and applicable shared
    sections
  - infer item-level options and toppings from both modifiables and descriptions
  - if the category shows quantity-based bundle pricing followed by unpriced
    choices, treat the quantity-price bundles as the main items
  - for bundle pricing like `2 Rolls $10, 3 Rolls $12`, create main items such
    as `2 Rolls` and `3 Rolls` with those prices
  - then extract the selectable choices as item-level options for each created
    bundle item, not as shared category options
  - set the option cardinality to match the bundle quantity, for example
    `minRequired=2, maxAllowed=2` for `2 Rolls`, and `minRequired=3,
    maxAllowed=3` for `3 Rolls`

Pricing guidance:

- If an item has one clear direct price, use it as `price`.
- If the item pricing is expressed entirely through item sizes, put the size
  prices in `ItemSizes` and use `price` only for the main/default price when one
  is clearly present.
- For option prices, convert them into `choicePrice` or `choicePriceBySize`.
- Never invent negative prices.

Output requirement:

- Return a single JSON object matching the target schema as closely as possible.
