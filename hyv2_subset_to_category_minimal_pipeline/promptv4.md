You are given a JSON input that was extracted by AI and may contain imperfect grouping or structure. You must restructure and correct the input to produce the best possible target JSON.

The input contains exactly one `normal_category` and zero or more related shared sections (`shared_sizes_section`, `shared_options_section`, etc.). Merge this information into a single JSON object matching the target `category_item_minimal.schema.json` format.

## Core Rules
1. **JSON Only:** Return a complete JSON response without markdown fences.
2. **No Hallucinations:** Do not invent information or negative prices. 
3. **Full Coverage:** Never skip any item, size, option, topping, or modifier that is present and can be represented in the schema.
4. **Scope:** Use the target category as the anchor. If a shared section applies to it, fold that information into the category output rather than preserving the shared section separately. Merge multiple shared sections if relevant.
5. **Fallback:** The category output must never end with zero items. If needed, create one fallback item using the category name and attach relevant details to it.

## Scope & Placement (Deduplication)
- Place data at the **category level** only when it applies to the whole category.
- Place data at the **item level** only when it applies to one specific item.
- **Never duplicate** the same sizes, options, or toppings at both levels.
- If structures overlap, keep the shared part at the category level and only the genuinely item-specific remainder at the item level.

## Interpreting Evidence
- Do not read descriptive fields (e.g., `category_description`, `item_description`, `category_type`, descriptions within prices/sizes) merely as verbatim text. 
- Use all available fields together to infer structural meaning (sizes, options, toppings, prices).
- *Passthrough Note:* Do not generate `category_description`, `item_description`, or `category_hours` fields in the output, as they are handled elsewhere. Use `category_type` to determine if toppings apply.

## Pricing & Sizes
1. **Direct Pricing:** If an item has one clear direct price, use it as `price`.
2. **Size Pricing:** If an item has sizes, its `price` must be `0` and prices go into `ItemSizes` or `category_sizes`.
3. **Base vs Add-on:** Treat size prices as full final prices. If there is a base price + sizes, create a size named "Regular" or "Standard" for the base price.
4. **Variants/Add-ons Printed as Full Prices:** If a variant (e.g., "Small with Cheese") is printed as a full price, DO NOT create a duplicate size. Instead, find the matching base item size price, and convert the variant into an incremental option price (e.g., +$3.00) for that size.
5. **Multiple Prices:** If multiple prices exist for the same item/option, infer them as different sizes with appropriate labels. Normalize size names consistently across the whole subset (e.g. choose one of `Sm`, `Small`).

## Options
- Prefer high recall: create options wherever reasonably supported (e.g., from descriptions, item names implying a variant, or shared sections).
- Always populate `optionName` (generate one if missing, representing the implied modifier heading).
- `choiceName` is the specific selectable choice. For simple add-ons (e.g., "add cheese"), make both names the same if no grouping label is provided.
- **Size-based Option Pricing:** Set `choicePrice` to `0` and populate `choicePriceBySize` using exact size labels.
- **Full Prices by Option:** If option prices are full final prices, treat the cheapest as the base price (price=0) and convert others to incremental differences.
- **Grouping & Constraints:** Options are independent by default. Group under the same `optionName` only if mutually exclusive. If explicit min/max are missing, default to `minRequired=0`, `maxAllowed=2`. Essential options use `minRequired=1`, `maxAllowed=1`. Include default essential components at price `0` when there are paid substitutions.

## Toppings
- Only populate toppings for pizzas, calzones, and strombolis.
- Default toppings are those already on the item; available toppings are additions.
- Always populate the `group` for available toppings using the topping heading.
- `priceHalf` is the half-topping price when listed.
- Carefully distinguish true toppings from non-topping options.

## Bundled Items
- If a category has quantity-based bundle pricing (e.g., "2 Rolls $10"), treat the quantity-price bundles as the main items.
- Extract selectable choices as item-level options for each bundle item (not shared category options).
- Match the option cardinality to the bundle quantity (e.g., `minRequired=2, maxAllowed=2` for 2 Rolls).
