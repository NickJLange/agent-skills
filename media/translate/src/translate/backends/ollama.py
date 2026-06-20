"""Ollama backend. Hits the local Ollama HTTP API (default localhost:11434).

Stdlib-only — uses urllib so the package has zero install-time dependencies.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


_SYSTEM_PROMPT = (
    "You are a precise translator. Translate the user's text into the target language. "
    "Preserve proper nouns, product names, code identifiers, URLs, and numbers exactly. "
    "Do not add commentary or wrap the output in quotes — return only the translated text."
)


class OllamaBackend:
    name = "ollama"

    def __init__(self, *, model: str | None = None, host: str | None = None, timeout: float | None = None):
        self.model = model or os.environ.get("TRANSLATE_MODEL", "qwen2.5:7b-instruct")
        self.host = (host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        timeout_ms = int(os.environ.get("TRANSLATE_TIMEOUT_MS", "30000"))
        self.timeout = (timeout if timeout is not None else timeout_ms / 1000.0)

    def translate(self, text: str, *, source: str, target: str) -> str:
        prompt = (
            f"Source language: {source}\n"
            f"Target language: {target}\n"
            f"Text:\n{text}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read())
        return (body.get("message") or {}).get("content", "").strip()
