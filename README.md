# battlecard-builder

Turn raw, messy competitor notes into a structured sales battlecard from the command line. Provider-swappable: runs on the Anthropic API or on Ollama Cloud's free models with a one-flag change.

The tool itself is small. The interesting part is what it taught me about where the quality of an AI tool actually lives — see [The prompt-iteration story](#the-prompt-iteration-story) below.

> **Note on the examples:** all sample data in this repo (NorthBeacon, Apex RiskShield) is **synthetic** — invented companies used as a test fixture. Nothing here is real competitive intelligence.

---

## What it does

Point it at a text file of notes about a competitor (plus a one-line description of your own company), and it produces a one-page Markdown battlecard: competitor positioning, where you beat them, where *they* beat *you*, objection handling, and trap-setting questions a rep can ask on a call.

```bash
python3 battlecard.py notes.txt
# -> writes notes-battlecard.md
```

## Quickstart

```bash
# 1. Clone and enter the repo, then set up an isolated environment
python3 -m venv venv
source venv/bin/activate

# 2a. To use the free Ollama Cloud path:
pip install openai
export OLLAMA_API_KEY=...        # free key from ollama.com -> account settings
python3 battlecard.py notes.txt --provider ollama --model gpt-oss:20b

# 2b. Or to use the Anthropic path:
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python3 battlecard.py notes.txt   # anthropic is the default provider
```

## How to write the input

The output is only as good as the notes. Two things matter: name the competitor explicitly, and give specifics (real numbers, not adjectives). Start the file with an `ABOUT US:` line so the tool has *your* side to work from, not just the competitor's.

```
ABOUT US: [company], we sell [product] to [segment]. We position on [positioning].
- [specific proof points about us: deployment time, certs, customers, a named win]

COMPETITOR NOTES: [Competitor Name]
- [their genuine strengths AND weaknesses — be honest about both]
- [specifics: pricing structure, deployment time, recent signals]
```

## Configuration

| Setting | How | Notes |
|---|---|---|
| Provider | `--provider {anthropic,ollama}` or `LLM_PROVIDER` env | Defaults to `anthropic`. |
| Model | `--model <name>` | Defaults to `claude-sonnet-4-6` / `gpt-oss:20b`. |
| System prompt | `--prompt <path>` | Defaults to `prompts/battlecard.md`. |
| Output | `-o <path>` | Defaults to `<notes>-battlecard.md`. |

A few things worth knowing:

- **Ollama's OpenAI-compatible endpoint is `https://ollama.com/v1`** — not `/api/v1`, which 404s.
- **The free tier only serves the smaller models.** The large ones (e.g. `gpt-oss:120b`) return a 403 asking you to upgrade. `gpt-oss:20b` works on the free tier. List what exists with `curl https://ollama.com/v1/models -H "Authorization: Bearer $OLLAMA_API_KEY"` — but note that list shows everything that *exists*, not what's free, so confirm by running.
- **The Anthropic default is Sonnet, not Opus, on purpose** — for battlecard synthesis the output is hard to distinguish, and a tool you run repeatedly shouldn't default to the most expensive model. Override with `--model claude-opus-4-8` if the gap ever matters.

---

## The prompt-iteration story

This is the part I'd actually want someone to read. The tool worked on the first try. It was *wrong* on the first try, and the gap between those two is the whole point.

**v1 — it ran, and it looked great.** The first version produced a clean, well-formatted battlecard with all the right sections. Easy to call it done. It wasn't.

**The failure.** Two problems hid under the polish. First, the card pretended I won on *everything* — it listed the competitor's genuine strengths (brand, breadth of integrations, big-logo credibility) and then steamrolled them in a "How We Win" section as if they didn't exist. A rep using that card walks into an enterprise deal thinking integration breadth is a non-issue and gets killed. Second, where my input was thin, the model didn't flag the gap — it *filled* it. It invented capabilities I never claimed ("we cover all major platforms"), a fake "positive G2 rating," and an "audit-ready tooling" advantage I never had. The pattern was specific and dangerous: **the model laundered thin input into confident, false claims, and it did this worst exactly where I had a real gap to hide.**

**The wrong diagnosis.** My first instinct was to blame the model — I was running a small, free one (`gpt-oss:20b`), and "small models can't follow instructions" is an easy story. I was ready to write a build-vs-buy conclusion: *pay for a bigger model.* That would have been wrong, and two confounds were the real cause. (1) I was still running the tool's generic default prompt, not a hardened one — so the guardrails I thought were in place didn't exist. (2) My test notes were vague, so the model had nothing real to work with and improvised. I had blamed the model for a gap I handed it.

**The fix.** Two changes, neither of which was "a bigger model." I rewrote the input to contain real specifics on both sides — including the competitor's *honest strengths*. And I rewrote the system prompt with enumerated, per-section grounding rules: every factual claim must trace to the notes or be marked `[not in notes]`; the rule applies to claims about *my own* side as strictly as the competitor's; a dedicated "Where They Beat Us" section is required, and if I have no honest counter to a competitor strength, the card must say `[no counter in notes]` rather than invent one. Small models follow crisp, enumerated rules far better than gentle ones, so the prompt got blunt and explicit.

**The result.** Same model, same notes — only the prompt changed. The new card conceded the competitor's brand and integration breadth honestly, flagged `[no counter in notes]` three times instead of fabricating, dropped every invented claim from before, and pulled in the real proof points the first version had ignored. The free 20B model held the line cleanly.

**The takeaway — and it's the opposite of where I started.** The bottleneck was never model size. Per-section, enumerated guardrails got a free small model to do work I'd assumed required a bigger, paid one. The expensive fix would have masked the real lesson: *for this task, prompt design is the lever, not model tier.*

**What's still broken.** It isn't perfect, and pretending otherwise would undercut the point. One conceded weakness — the competitor's mature audit tooling — still gets quietly reframed as a win by pointing at my certifications, which aren't the same thing. The model found one seam in the guardrail. That's the next thing to harden, and it's a fair illustration that grounding rules reduce fabrication without fully eliminating it on a small model.

## Limitations

- Output quality is bounded by input quality. Vague notes produce flagged gaps (good) or, on a weak model, occasional overreach (see above).
- The free Ollama tier is rate-limited and serves only smaller models; expect a `429` under load and retry after ~30s.
- This is a personal build for learning and demonstration, not a production tool.

## Repo structure

```
battlecard.py            # the CLI (provider-swappable)
prompts/battlecard.md    # the hardened system prompt
requirements.txt
notes.txt                # synthetic example input
```
