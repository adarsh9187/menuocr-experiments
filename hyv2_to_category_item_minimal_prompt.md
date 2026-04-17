You are given a JSON input that contains:

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
4. Preserve verbatim printed category and item descriptions where the target
   schema expects them.
5. Convert natural-language modifiable text into structured fields only when the
   information is stated clearly enough.
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
  - use the target category's verbatim category description
- `category_sizes`:
  - populate from shared size sections or category-level size information that
    applies to the target category
- `category_options`:
  - populate from shared option/modifier sections or category-level options that
    apply to the target category
- `category_toppings`:
  - populate from shared topping sections or category-level topping information
    that applies to the target category
- `items`:
  - create item entries from the target category's item list
  - enrich each item with item-level descriptions, prices, sizes, options, and
    toppings that can be derived from the target category and applicable shared
    sections

Pricing guidance:

- If an item has one clear direct price, use it as `price`.
- If the item pricing is expressed entirely through item sizes, put the size
  prices in `ItemSizes` and use `price` only for the main/default price when one
  is clearly present.
- For option prices, convert them into `choicePrice` or `choicePriceBySize`.
- Never invent negative prices.

Output requirement:

- Return a single JSON object matching the target schema as closely as possible.
