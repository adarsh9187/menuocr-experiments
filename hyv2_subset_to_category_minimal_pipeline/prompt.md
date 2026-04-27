You are given a JSON input that was extracted by AI and may contain imperfect
grouping or structure. You may restructure and correct the input as needed,
following the rules below, in order to produce the best possible target JSON.

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
4. Return a complete response.
5. Never skip any item, size, option, topping, modifier, or other modifiable
   that is present in the input and can be represented in the target schema.
6. Use descriptions and modifiables as supporting evidence to derive structured
   sizes, options, toppings, prices, and rules when the information is stated
   clearly enough.
7. If a shared section applies to the target category, fold that information
   into the target category output instead of preserving the shared section as a
   separate object.
8. If multiple shared sections contribute relevant information, merge them.
9. Use the target category as the scope anchor for all decisions.
10. Capture all important prices, sizes, options, toppings, and item-specific
   rules that can be structured from the input subset.
11. When in doubt, prefer preserving information in the closest valid target
   field rather than dropping it.

Placement and deduplication rules:

- For fields that can appear at both category level and item level, place the
  data at category level when it applies to the whole category.
- Place the data at item level when it applies only to one specific item.
- Make sure the final output covers the full applicable content of the input.
- Do not omit any valid item-level or category-level information just because it
  also appears alongside other structured data.
- Do not create duplicates across category level and item level.
- Do not repeat the same structured information more than once in the final
  output.

Descriptions:

- Populate `category_description` from the input's category-level description
  fields as-is.
- Populate `itemDescription` from the input's item-level description fields
  as-is.

Pricing and sizes:

- If an item has one clear direct price, use it as `price`.
- If an item has sizes, `price` must be `0` and all prices must be populated in
  `ItemSizes` or `category_sizes`, whichever is applicable.
- If multiple prices exist for the same item or option, infer them as different
  sizes whenever that is the best fit.
- Understand and assign the correct size labels for those inferred prices.
- If item pricing is expressed through sizes, put the size prices in
  `ItemSizes`.
- If category-wide pricing is expressed through shared sizes, place it in
  `category_sizes`.
- For option prices, convert them into `choicePrice` or `choicePriceBySize`.
- Never invent negative prices.

Options:

- Populate options at category level when they apply to the whole category, and
  at item level when they apply only to an individual item.
- Do not duplicate the same options at both levels.
- Infer options from both modifiables and description fields whenever the
  structure is clear enough.
- `optionName` is the modifier heading name and must be populated whenever
  present.
- If a heading is not explicitly present, generate an `optionName` that matches
  the modifier heading implied by the choice.
- `choiceName` is the specific selectable choice under that modifier heading.
- Options must be created independently of each other by default.
- Group choices under the same `optionName` only when the choices are mutually
  exclusive.
- If an essential component is mentioned and there are paid substitutions,
  group them together and include the default essential component at price 0.
- If explicit min/max are not stated, default to `minRequired=0` and
  `maxAllowed=2`.
- If the option is essential to complete the order, use
  `minRequired=1, maxAllowed=1`.

Toppings:

- Populate toppings at category level when they apply to the whole category,
  and at item level when they apply only to an individual item.
- Do not duplicate the same toppings at both levels.
- Infer toppings from both modifiables and description fields whenever the
  structure is clear enough.
- Default toppings are the toppings already on the item.
- Available toppings are the toppings that can be added.
- Always populate the `group` for available toppings using the heading that the
  toppings belong to.
- `priceHalf` is the half-topping price whenever that is listed.

Items:

- Create item entries from the target category's item list.
- Enrich each item with item-level prices, sizes, options, and toppings that
  can be derived from the target category and applicable shared sections.
- If the category shows quantity-based bundle pricing followed by unpriced
  choices, treat the quantity-price bundles as the main items.
- For bundle pricing like `2 Rolls $10, 3 Rolls $12`, create main items such as
  `2 Rolls` and `3 Rolls` with those prices.
- Then extract the selectable choices as item-level options for each created
  bundle item, not as shared category options.
- Set the option cardinality to match the bundle quantity, for example
  `minRequired=2, maxAllowed=2` for `2 Rolls`, and `minRequired=3,
  maxAllowed=3` for `3 Rolls`.

Output requirement:

- Return a single JSON object matching the target schema as closely as possible.
