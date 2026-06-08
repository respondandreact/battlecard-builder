# battlecard-builder

A small Python CLI that turns a text file of raw competitor notes into a
sales-ready competitive battlecard using the Anthropic API (Claude).

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```bash
# Writes notes-battlecard.md next to the input file
python battlecard.py notes.txt

# Choose the output path
python battlecard.py notes.txt -o acme-battlecard.md
```

The system prompt lives in [`prompts/battlecard.md`](prompts/battlecard.md);
edit it to change the battlecard's structure or tone. Override it per-run with
`--prompt`, and pick a different model with `--model`. Run
`python battlecard.py --help` for all options.
