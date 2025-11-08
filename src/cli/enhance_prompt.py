from __future__ import annotations

import json
from typing import List, Optional

# Optional dependency: Click. We fall back to argparse when missing.
try:
    import click  # type: ignore
except Exception:  # pragma: no cover
    click = None  # type: ignore

import argparse

from src.cli.interactive_prompt_enhancer import InteractivePromptEnhancer


def run_cli_logic(argv: Optional[List[str]] = None) -> dict:
    """Argument parsing + enhancement logic returning a dict for testability.

    This path uses argparse so it works without external dependencies.
    """
    parser = argparse.ArgumentParser(description="Context Prompt Enhancer (safe fallback)")
    parser.add_argument("--input", "-i", type=str, required=True, help="Prompt text to enhance")
    ns = parser.parse_args(argv)

    enhancer = InteractivePromptEnhancer()
    result = enhancer.enhance_once(ns.input)
    return result.to_dict()


# Optional nicer CLI using Click if available. Tests do not rely on this path.
if click is not None:  # pragma: no cover - exercised in manual usage when click is installed

    @click.command(name="context-enhance-prompt")
    @click.option("--input", "input_text", required=True, help="Prompt text to enhance")
    def click_main(input_text: str) -> None:
        payload = run_cli_logic(["--input", input_text])
        print(json.dumps(payload, ensure_ascii=False))


def main() -> None:
    """Entry point used by `python -m` or console scripts.
    Always available regardless of click installation.
    """
    payload = run_cli_logic()
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover
    main()

