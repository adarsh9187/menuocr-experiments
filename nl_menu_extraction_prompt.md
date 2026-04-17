# Experimental Natural-Language Menu Extraction Prompt

Use this prompt with the experimental schema in
[nl_menu_extraction.schema.json](/home/softsensor/AntiGrav/Menu/experiments/nl_menu_extraction.schema.json).

## Prompt

Extract the menu into the provided JSON schema.

This experiment does not want a single response for the whole menu, and it does
not want per-item structured lists.

Instead, return:

1. one `global_response` for anything that applies to the menu as a whole
2. one narrative `response` for each category or menu section

Follow these rules carefully:

1. Do not emit item arrays.
2. Do not emit separate option arrays, topping arrays, or ambiguity arrays.
3. Each category should be represented by one prose response.
4. Cover categories in visual reading order.
5. Within each category response, every item name must be in double quotation
   marks.
6. For each quoted item, describe:
   - its visible price or price pattern
   - any sizes, variants, or quantity pricing
   - any options, toppings, substitutions, or add-ons
   - how it appears on the menu visually
7. Also describe category-level shared structures in prose when present:
   - shared size tables
   - shared topping lists
   - shared protein pricing
   - shared modifiers
   - shared disclaimers
   - shared preparation notes
8. Never miss important information. Prices, options, descriptions, sizes,
   shared rules, substitutions, add-ons, and other menu-defining details must
   always be carried into the response when they are visible.
8. Put menu-wide information only in `global_response`, such as:
   - restaurant/menu identity
   - overall layout
   - hours
   - repeated disclaimers
   - global pricing notes
9. When something is unclear, do not force a clean structural answer. Instead,
   explain what it looks like visually and why that makes the interpretation
   uncertain.
10. Do not invent missing prices, descriptions, or rules.
11. Keep the writing concise. The response should be compact and efficient, but
    it must still include all important information.

Style requirements:

- write complete descriptive prose
- every item name must be in double quotation marks
- mention visual layout cues when they matter
- distinguish explicit printed facts from interpretation
- be concise without dropping important facts

Good style for a category response:

- The Appetizers section appears in the upper left portion of the menu with a
  bold heading and tightly stacked rows. "Spring Rolls" and "Crab Rangoon" each
  appear on their own line with a single right-aligned price, while "Sampler
  Platter" is followed by a smaller descriptive line underneath, making it look
  like a standalone item with no visible size choices. A note about dipping
  sauce appears directly below the item block and seems to apply to the whole
  section rather than to one item.

Good style for global response:

- The menu appears to be organized in two columns with decorative headers and
  repeated footer notes. The restaurant name is centered at the top, the hours
  appear in a boxed block near the bottom, and a disclaimer about prices being
  subject to change is repeated in several sections, which suggests it is a
  menu-wide note rather than category-specific text.

Avoid style like:

- Category: Appetizers
- Item: "Spring Rolls"
- Price: 7.95

Instead, keep each category as one coherent narrative block.
