#!/usr/bin/env python3
"""Build a competitive battlecard from raw competitor notes using the Anthropic API.

Reads a plaintext file of raw competitor notes, sends it to Claude with the
system prompt stored in prompts/battlecard.md, and writes the generated
battlecard to a Markdown file.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python battlecard.py notes.txt
    python battlecard.py notes.txt -o acme-battlecard.md
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import anthropic

API_KEY_ENV = "ANTHROPIC_API_KEY"
DEFAULT_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "battlecard.md"
DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_TOKENS = 16000


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a competitive battlecard from raw competitor notes.",
    )
    parser.add_argument(
        "notes",
        type=Path,
        help="Path to a text file of raw competitor notes.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Path for the generated Markdown battlecard "
        "(default: <notes>-battlecard.md).",
    )
    parser.add_argument(
        "-p",
        "--prompt",
        type=Path,
        default=DEFAULT_PROMPT_PATH,
        help=f"Path to the system prompt (default: {DEFAULT_PROMPT_PATH}).",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_MODEL,
        help=f"Claude model to use (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Maximum output tokens (default: {DEFAULT_MAX_TOKENS}).",
    )
    return parser.parse_args(argv)


def read_text(path: Path, label: str) -> str:
    """Read a UTF-8 text file, exiting with a friendly message on failure."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        sys.exit(f"error: {label} not found: {path}")
    except OSError as exc:
        sys.exit(f"error: could not read {label} ({path}): {exc}")
    if not text.strip():
        sys.exit(f"error: {label} is empty: {path}")
    return text


def generate_battlecard(
    notes: str, system_prompt: str, model: str, max_tokens: int
) -> str:
    """Send the notes to Claude and return the generated battlecard text."""
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": notes}],
    ) as stream:
        message = stream.get_final_message()
    return "".join(block.text for block in message.content if block.type == "text")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if not os.environ.get(API_KEY_ENV):
        sys.exit(f"error: {API_KEY_ENV} environment variable is not set.")

    notes = read_text(args.notes, "competitor notes")
    system_prompt = read_text(args.prompt, "system prompt")

    output_path = args.output or args.notes.with_name(
        f"{args.notes.stem}-battlecard.md"
    )

    try:
        battlecard = generate_battlecard(
            notes, system_prompt, args.model, args.max_tokens
        )
    except anthropic.APIError as exc:
        sys.exit(f"error: Anthropic API request failed: {exc}")

    if not battlecard.strip():
        sys.exit("error: the model returned an empty battlecard.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_path.write_text(battlecard, encoding="utf-8")
    except OSError as exc:
        sys.exit(f"error: could not write output ({output_path}): {exc}")

    print(f"Wrote battlecard to {output_path}")


if __name__ == "__main__":
    main()
