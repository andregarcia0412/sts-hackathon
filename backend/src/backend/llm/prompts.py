"""Registry of every prompt sent to the LLM, so each analysis can record the hash of what it used."""

import hashlib

_PROMPTS: dict[str, str] = {}


def register_prompt(name: str, text: str) -> str:
    _PROMPTS[name] = text
    return text


def prompt_hashes() -> dict[str, str]:
    return {name: hashlib.sha256(text.encode()).hexdigest()[:12] for name, text in sorted(_PROMPTS.items())}
