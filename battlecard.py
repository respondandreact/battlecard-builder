#!/usr/bin/env python3
"""
battlecard.py — turn raw competitor notes into a sales battlecard.

Provider-swappable: runs on the Anthropic API (default) or on Ollama Cloud's
free OpenAI-compatible endpoint. The system prompt and CLI behavior are
identical across providers; only the model call differs.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...        # for the default provider
    python battlecard.py notes.txt             # -> notes-battlecard.md

    export OLLAMA_API_KEY=...                   # for the free Ollama path
    LLM_PROVIDER=ollama python battlecard.py notes.txt
    python battlecard.py notes.txt --provider ollama --model gpt-oss:120b-cloud
"""

import argparse
import os
import sys
from pathlib import Path

# --- Defaults -----------------------------------------------------------------
DEFAULT_PROMPT_PATH = "prompts/battlecard.md"

# Sensible per-provider model defaults. Anthropic defaults to Sonnet (not Opus)
# on purpose: this tool gets run repeatedly, and on battlecard synthesis Sonnet's
# output is hard to distinguish from Opus while being cheaper and faster. Bump to
# claude-opus-4-8 with --model if you ever find the quality gap matters.
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "ollama": "gpt-oss:120b-cloud",  # verify availability with `ollama ls`
}

# Ollama Cloud's OpenAI-compatible base URL. Note: it is /v1, NOT /api/v1.
OLLAMA_BASE_URL = "https://ollama.com/v1"


def fail(msg: str) -> "None":
    """Print a clean error and exit non-zero (no stack trace for user errors)."""
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


# --- Provider implementations -------------------------------------------------
# Each returns the battlecard text as a string. SDKs are imported lazily so you
# only need the SDK for the provider you actually use.

def generate_anthropic(system_prompt: str, notes: str, model: str) -> str:
    try:
        import anthropic
    except ImportError:
        fail("the 'anthropic' package is not installed. Run: pip install anthropic")

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    chunks = []
    try:
        # Streaming is the recommended pattern for variable-length output; it
        # also avoids HTTP read timeouts on longer battlecards.
        with client.messages.stream(
            model=model,
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": notes}],
        ) as stream:
            for text in stream.text_stream:
                chunks.append(text)
    except anthropic.APIError as e:
        fail(f"Anthropic request failed: {e}")
    return "".join(chunks)


def generate_ollama(system_prompt: str, notes: str, model: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        fail("the 'openai' package is not installed. Run: pip install openai")

    # Ollama Cloud speaks the OpenAI protocol, so we reuse the OpenAI SDK and
    # just repoint the base_url. The API key comes from OLLAMA_API_KEY.
    client = OpenAI(
        base_url=OLLAMA_BASE_URL,
        api_key=os.environ["OLLAMA_API_KEY"],
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": notes},
            ],
        )
    except Exception as e:  # noqa: BLE001 - we want a friendly message either way
        # The free tier is rate limited (per-model, undocumented). Surface 429s
        # clearly rather than dumping a traceback.
        if "429" in str(e) or "rate" in str(e).lower():
            fail(
                "Ollama Cloud rate limit hit (429). Wait ~30s and retry, "
                "or try a different model with --model."
            )
        fail(f"Ollama request failed: {e}")
    return resp.choices[0].message.content or ""


PROVIDERS = {
    "anthropic": (generate_anthropic, "ANTHROPIC_API_KEY"),
    "ollama": (generate_ollama, "OLLAMA_API_KEY"),
}


# --- CLI ----------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Turn raw competitor notes into a sales battlecard."
    )
    parser.add_argument("notes", help="Path to a text file of raw competitor notes.")
    parser.add_argument(
        "-o", "--output",
        help="Output path (default: <notes>-battlecard.md).",
    )
    parser.add_argument(
        "--provider",
        choices=sorted(PROVIDERS),
        help="LLM provider. Overrides the LLM_PROVIDER env var. Default: anthropic.",
    )
    parser.add_argument(
        "--model",
        help="Model to use. Defaults to a sensible model for the chosen provider.",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT_PATH,
        help=f"Path to the system prompt (default: {DEFAULT_PROMPT_PATH}).",
    )
    args = parser.parse_args()

    # Resolve provider: --provider > LLM_PROVIDER env > "anthropic".
    provider = args.provider or os.environ.get("LLM_PROVIDER", "anthropic")
    if provider not in PROVIDERS:
        fail(f"unknown provider '{provider}'. Choose one of: {', '.join(sorted(PROVIDERS))}")
    generate, key_env = PROVIDERS[provider]

    # Validate inputs up front so failures are fast and obvious.
    if not os.environ.get(key_env):
        fail(f"{key_env} is not set (required for provider '{provider}').")

    notes_path = Path(args.notes)
    if not notes_path.is_file():
        fail(f"notes file not found: {notes_path}")
    notes = notes_path.read_text(encoding="utf-8").strip()
    if not notes:
        fail(f"notes file is empty: {notes_path}")

    prompt_path = Path(args.prompt)
    if not prompt_path.is_file():
        fail(f"system prompt not found: {prompt_path}")
    system_prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not system_prompt:
        fail(f"system prompt is empty: {prompt_path}")

    model = args.model or DEFAULT_MODELS[provider]
    out_path = Path(args.output) if args.output else notes_path.with_name(
        f"{notes_path.stem}-battlecard.md"
    )

    print(f"[{provider}] generating battlecard with {model}...", file=sys.stderr)
    battlecard = generate(system_prompt, notes, model).strip()
    if not battlecard:
        fail("model returned an empty response; nothing written.")

    # Only write on success — no partial files on error.
    out_path.write_text(battlecard + "\n", encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
