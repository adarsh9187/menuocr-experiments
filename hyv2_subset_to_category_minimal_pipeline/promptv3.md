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

About the input subset:

- The target category and related shared sections may express important menu
  logic across:
  - `category_description`
  - `category_hours`
  - `category_type`
  - `category_sizes`
  - `category_options`
  - `category_toppings`
  - `category_pricing`
  - `item_description`
  - `item_sizes`
  - `item_options`
  - `item_toppings`
  - `item_pricing`
  - `item_rules_or_notes`
  - item names and category names
- These fields are descriptive evidence, not already-final structured output.
- The descriptive fields are not guaranteed to be full prose. They may be rich
  descriptive text, compact shorthand, fragments, partial price strings, terse
  modifier labels, or mixed natural language plus symbols.
- You must semantically understand these fields rather than reading them
  literally as plain descriptions. Use them to infer structure when supported by
  the input.
- In particular, distinguish carefully between:
  - direct item prices
  - item sizes
  - category-wide sizes
  - ordinary options
  - toppings
  - size-based option pricing
- When the same short text could be interpreted in multiple ways, use the
  surrounding category, shared sections, item names, descriptions, and pricing
  patterns to determine whether it represents a size, an option, a topping, a
  direct price, or a size-based option.
- Normalize size names consistently across the whole subset. If the menu uses
  short forms or inconsistent variants such as `Sm`, `Small`, `Md`, `Medium`,
  `Lg`, or `Large`, use one normalized size name consistently across
  category-level size definitions and item-level size-based options.

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
6. Use descriptions and split descriptive fields as supporting evidence to
   derive structured sizes, options, toppings, prices, and rules when the
   information is stated clearly enough.
7. Infer every modifiable type from all relevant evidence, not only its matching
   field. In particular:
   - infer options from category/item descriptions, category/item pricing, and
     category/item options fields
   - infer sizes from category/item descriptions, category/item pricing, and
     category/item sizes fields
   - infer toppings from category/item descriptions, category/item pricing, and
     category/item toppings fields when that evidence supports them
   - use the matching field plus descriptions plus pricing together whenever you
     decide whether something is an option, size, or topping
8. If a shared section applies to the target category, fold that information
   into the target category output instead of preserving the shared section as a
   separate object.
9. If multiple shared sections contribute relevant information, merge them.
10. Use the target category as the scope anchor for all decisions.
11. Capture all important prices, sizes, options, toppings, and item-specific
   rules that can be structured from the input subset.
12. When in doubt, prefer preserving information in the closest valid target
   field rather than dropping it.

Placement and deduplication rules:

- For fields that can appear at both category level and item level, place the
  data at category level when it applies to the whole category.
- Place the data at item level when it applies only to one specific item.
- Never duplicate the same sizes, options, or toppings at both category level
  and item level. If something is truly shared across the category, keep it
  only at category level. If something is truly specific to one item, keep it
  only at that item level.
- Do not copy item-level sizes, options, or toppings upward into category
  level just because similar information exists elsewhere in the subset.
- Do not copy category-level sizes, options, or toppings downward onto every
  item unless an item truly has its own distinct item-level version of that
  same structure.
- If category-level and item-level structures overlap, keep the shared/common
  part only at category level and keep only the genuinely item-specific
  remainder at item level.
- Make sure the final output covers the full applicable content of the input.
- Do not omit any valid item-level or category-level information just because it
  also appears alongside other structured data.
- Do not create duplicates across category level and item level.
- Do not repeat the same structured information more than once in the final
  output.
- The category output must never end with zero items. If the target category has
  no usable item entries after interpretation, create one fallback item using
  the category name itself as the item name, then attach the category's relevant
  prices, sizes, options, toppings, and descriptive evidence to that fallback
  item as best as the schema allows.
  
Descriptions and passthrough fields:

- Use `category_description` and `item_description` as hints for understanding
  pricing, sizes, options, toppings, and item structure.
- Do not generate category description or item description fields in the output.
  They will be passed through unchanged later by the pipeline.
- Use `category_hours` only as supporting evidence about operating-hour scope.
  Do not generate any hours field in the output.
- Use `category_type` as a hint for category semantics, especially when
  deciding whether toppings are appropriate.

Pricing and sizes:

- If an item has one clear direct price, use it as `price`.
- If an item has sizes, `price` must be `0` and all prices must be populated in
  `ItemSizes` or `category_sizes`, whichever is applicable.
- If an item has a base price and also sizes, create a size entry named
  `Regular` or `Standard` for the base price and include the other size entries
  alongside it.
- Treat size prices as full final prices for those sizes, not as incremental
  upcharges.
- If the menu gives one set of full prices for the base item by size and a
  second set of full prices for an add-on or variant by those same sizes, keep
  only the true base sizes in `ItemSizes` and create an option for the add-on
  or variant instead of creating duplicate variant sizes.
- In that pattern, `ItemSizes` should contain only the base item full prices by
  size, and the add-on or variant should be represented as an option with
  `choicePrice=0` and `choicePriceBySize` populated using the incremental
  difference from the corresponding base size price.
- For example, if Small is 4.99, Large is 8.99, Small with cheese is 7.99, and
  Large with cheese is 11.99, then `ItemSizes` should remain Small 4.99 and
  Large 8.99, while the cheese option should have size-based increments of 3.00
  for Small and 3.00 for Large.
- If multiple prices exist for the same item or option, infer them as different
  sizes whenever that is the best fit.
- Understand and assign the correct size labels for those inferred prices.
- If item pricing is expressed through sizes, put the size prices in
  `ItemSizes`.
- If category-wide pricing is expressed through shared sizes, place it in
  `category_sizes`.
- Use `category_pricing`, `item_pricing`, `category_sizes`, and `item_sizes`
  together when deciding how prices and sizes should be structured.
- The category-level descriptive fields are not just verbatim storage buckets:
  `category_sizes`, `category_options`, `category_toppings`, and
  `category_pricing` should read like clear natural-language explanations you
  would give to a customer, while still preserving exact labels and prices.
- For option prices, convert them into `choicePrice` or `choicePriceBySize`.
- Never invent negative prices.

Options:

- Populate options at category level when they apply to the whole category, and
  at item level when they apply only to an individual item.
- Do not duplicate the same options at both levels.
- Prefer high recall for option extraction: create options wherever they are
  reasonably supported by the input, including from item names, category names,
  descriptions, split descriptive fields, and shared sections, even when the
  option is implied rather than introduced by an explicit modifier heading.
- Infer options from descriptive fields whenever the structure is clear enough.
- Treat item names and category names as evidence for options when they imply a
  selectable variant, flavor, protein, preparation, sauce, crust, topping set,
  or other modifier-like choice that a customer would reasonably understand as a
  structured option.
- `optionName` is the modifier heading name and must be populated whenever
  present.
- If a heading is not explicitly present, generate an `optionName` that matches
  the modifier heading implied by the choice.
- `choiceName` is the specific selectable choice under that modifier heading.
- For simple add-on options such as `add cheese`, `add bacon`, `extra sauce`,
  or similar addition-style modifiers, make `optionName` and `choiceName` the
  same text when no better grouping label is explicitly provided. For example,
  use `optionName = "Add Cheese"` and `choiceName = "Add Cheese"`.
- If an option has size-based pricing, set `choicePrice` to `0` and populate
  `choicePriceBySize` using the exact printed size labels from the input.
- When a variant or add-on is printed as full prices by size, do not copy those
  full prices directly into `choicePriceBySize`. First determine the matching
  base item size prices, then convert the variant pricing into incremental
  differences for each size.
- If the menu writes option prices as full final prices by option rather than
  explicit increments, treat the cheapest applicable choice as the base price
  and convert the more expensive choices into incremental differences relative
  to that cheapest base choice.
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
- Only populate toppings for pizzas, calzones, and strombolis. Do not populate
  toppings for other category or item types.
- Do not duplicate the same toppings at both levels.
- Infer toppings from descriptive fields whenever the structure is clear enough.
- Keep default toppings only at item level during generation.
- Keep available toppings only at category level during generation.
- Do not place default toppings in `category_toppings`.
- Do not place available toppings in item-level `toppings` during generation.
- The pipeline will append category-level available toppings back onto items
  after generation, so do not duplicate them yourself.
- Default toppings are the toppings already on the item.
- Available toppings are the toppings that can be added.
- Always populate the `group` for available toppings using the heading that the
  toppings belong to.
- Use `category_toppings`, `item_toppings`, `category_options`, and
  `item_options` carefully to distinguish true toppings from non-topping
  options.
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
