"""Backend protocol + registry. Selected at runtime by TRANSLATE_BACKEND env or --backend."""
from __future__ import annotations

import os
from typing import Protocol


class Backend(Protocol):
    name: str

    def translate(self, text: str, *, source: str, target: str) -> str: ...


def get_backend(name: str | None = None, *, model: str | None = None):
    name = name or os.environ.get("TRANSLATE_BACKEND", "ollama")
    if name == "noop":
        from .noop import NoopBackend
        return NoopBackend()
    if name == "ollama":
        from .ollama import OllamaBackend
        return OllamaBackend(model=model)
    raise ValueError(f"unknown backend: {name}")
