# Experiments

Scratch area for trying alternative menu extraction approaches before wiring them
into the main `.menu` and `.rmf` generation pipeline.

## Natural-Language CLI

The first experimental pipeline lives in
[run_nl_extraction.py](/home/softsensor/AntiGrav/Menu/experiments/run_nl_extraction.py).

It mirrors the existing `menuocr` environment pattern:

- loads `experiments/.env`
- falls back to `menuocr/.env`
- parses a menu file with ADE
- extracts against the experimental natural-language schema

Example:

```bash
python experiments/run_nl_extraction.py path/to/menu.pdf --save-markdown
```

Outputs go to `experiments/outputs/` by default.

## Nova Pro CLI

There is also a Nova Pro variant at
[run_nova_nl_extraction.py](/home/softsensor/AntiGrav/Menu/experiments/run_nova_nl_extraction.py).

It uses the AWS credentials in `experiments/.env`, converts PDFs to images, and
sends the images plus the experimental schema/prompt to Amazon Nova Pro through
Bedrock.

Example:

```bash
python experiments/run_nova_nl_extraction.py path/to/menu.pdf
```
