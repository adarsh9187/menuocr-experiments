# Natural-Language-First Extraction Plan

This experiment assumes the current ADE extraction is too rigid because it asks
for target-shaped structure too early.

The proposed alternative is:

1. extract menu information in rich natural language first
2. translate that natural-language record into a custom semantic structure
3. generate `.menu` and `.rmf` from code later

For now, this directory only focuses on step 1.

## Hypothesis

Natural-language extraction will perform better on real-world menu ambiguity
because it can preserve uncertainty and context before we force decisions such
as:

- whether something is a category-level vs item-level option
- whether an option group is a modifier or a preference
- whether a phrase implies sizes, variants, styles, combos, or add-ons
- whether repeated text is global, category-level, or item-level

## Immediate Experiment Goal

Produce a menu understanding artifact in natural language that is:

- faithful to the source
- comprehensive
- explicit about uncertainty
- explicit about scope
- easy to translate into a stricter internal structure later

## What the Natural-Language Artifact Should Capture

The extractor should describe:

### Document-level facts

- restaurant/menu title if visible
- source pages or sections
- document-wide notes
- global hours
- document-level disclaimers

### Category-level facts

- category name
- category description
- category ordering
- category-level hours
- category-level sizes if shared
- category-level modifiers/add-ons if shared
- category-level topping rules if shared
- whether a category seems to belong to food, beverage, alcohol, dessert, etc.

### Item-level facts

- item name
- item description
- standalone price
- size/variant pricing
- required choices
- optional add-ons
- included/default components
- removable components if explicitly stated
- toppings
- combo structure
- PLU or item code if visible

### Ambiguity/provenance facts

- source snippet or section reference for each claim when practical
- confidence notes
- unresolved ambiguity notes
- alternative interpretations when the menu is unclear

## Proposed Output Style

The first experiment should not try to emit `.menu`, RMF, or even the current
minimal payload.

It should emit a structured natural-language report with stable sections such as:

1. Menu overview
2. Global hours
3. Categories in order
4. For each category:
   - category summary
   - shared sizes/options/toppings/hours
   - items in order
5. Ambiguities and open questions
6. Explicitly missing information

## Recommended Extraction Principles

### 1. Preserve ambiguity instead of collapsing it

Bad:

- "This is definitely a modifier group"

Better:

- "The menu presents 'Choose Your Side' as a required choice with one selection;
  this likely maps to a preference/prompt rather than an optional modifier"

### 2. Preserve scope carefully

The extractor should always try to say whether a fact applies to:

- the whole menu
- a category
- a specific item
- a specific size of an item

### 3. Preserve evidence

Whenever practical, note the evidence in natural language:

- page/section
- nearby wording
- whether it came from repeated boilerplate or unique item text

### 4. Do not normalize too aggressively

Avoid premature decisions like:

- forcing title case
- deduping similar names too early
- assigning artificial IDs
- inventing absent prices
- converting uncertain wording into hard constraints

### 5. Make translator-friendly statements

Even though the output is natural language, it should use consistent phrasing so
that a second LLM or deterministic parser can later translate it.

## Draft Target Shape for the Natural-Language Artifact

This is not final, but it is a good first contract for experiments:

```md
# Menu Overview
- Restaurant/menu name: ...
- Document scope: ...

# Global Hours
- Monday: ...
- Tuesday: ...

# Categories
## 1. Appetizers
- Description: ...
- Category type guess: food / appetizers
- Shared sizes: ...
- Shared option groups:
  - ...
- Shared toppings:
  - ...
- Items:
  - Garlic Bread
    - Description: ...
    - Base price: ...
    - Sizes:
      - Small: ...
      - Large: ...
    - Required choices:
      - ...
    - Optional add-ons:
      - ...
    - Default toppings:
      - ...
    - Available toppings:
      - ...
    - Notes/ambiguities: ...

# Ambiguities
- ...

# Missing Information
- ...
```

## Future Translation Goal

The future translator should map this artifact into a custom semantic IR that is
closer to menu meaning than either:

- the current ADE minimal schema
- the current Menufy `.menu` schema
- raw RMF tables

That future IR should then be rendered into:

- `.menu`
- `.rmf`

by deterministic code where possible.

## Suggested Next Step

The next useful experiment is to create a first prompt and a sample output file
for one real menu document under `experiments/`, using this natural-language
contract and explicitly logging ambiguity instead of forcing schema-shaped
answers.
