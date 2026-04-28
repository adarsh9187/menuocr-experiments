# Hyv2 Subset To Category Minimal

This package contains the modular implementation behind
`experiments/hyv2_subset_to_category_minimal.py`.

Structure:

- `cli.py`: argument parsing, env loading, file I/O, user-facing errors
- `config.py`: default paths and Azure model config
- `client.py`: Azure OpenAI HTTP call and credential resolution
- `prompting.py`: prompt + schema + subset message assembly
- `normalize.py`: post-model cleanup and defensive normalization
- `models.py`: Pydantic validation models for the target payload
- `pipeline.py`: orchestration from subset payload to validated output
- `prompt.md`: task instructions sent to the model

Generation modes:

- `json_mode`: current behavior. Ask the model for JSON, then normalize and
  validate with Pydantic.
- `structured`: send the same prompt, but constrain generation with a strict
  JSON Schema derived from the Pydantic models via Azure OpenAI structured
  outputs.

CLI:

- `python -m experiments.hyv2_subset_to_category_minimal_pipeline.cli input.json`
- `python -m experiments.hyv2_subset_to_category_minimal_pipeline.cli input.json --generation-mode structured`
