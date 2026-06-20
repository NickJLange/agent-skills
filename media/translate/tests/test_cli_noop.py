"""End-to-end CLI test using the noop backend — no network, no LLM."""
from __future__ import annotations

import io
import json
import os
import sys

import pytest

from translate.cli import main


def _run(input_doc, args, monkeypatch, tmp_path):
    monkeypatch.setenv("TRANSLATE_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_doc)))
    buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", buf)
    code = main(args)
    return code, json.loads(buf.getvalue())


def test_noop_adds_lang_siblings(monkeypatch, tmp_path):
    doc = {"title": "Hello", "days": [{"heading": "H", "items": [{"title": "X", "summary": "S"}]}]}
    code, out = _run(doc, ["--target", "en", "--backend", "noop"], monkeypatch, tmp_path)
    assert code == 0
    assert out["title_en"] == "[en] Hello"
    assert out["days"][0]["heading_en"] == "[en] H"
    assert out["days"][0]["items"][0]["title_en"] == "[en] X"
    assert out["days"][0]["items"][0]["summary_en"] == "[en] S"


def test_noop_inplace_replaces(monkeypatch, tmp_path):
    doc = {"title": "Hello"}
    code, out = _run(doc, ["--target", "en", "--backend", "noop", "--inplace"], monkeypatch, tmp_path)
    assert code == 0
    assert out["title"] == "[en] Hello"
    assert "title_en" not in out


def test_idempotent_skip_already_translated(monkeypatch, tmp_path):
    doc = {"title": "Hello", "title_en": "preserved"}
    code, out = _run(doc, ["--target", "en", "--backend", "noop"], monkeypatch, tmp_path)
    assert code == 0
    assert out["title_en"] == "preserved"


def test_cache_round_trip(monkeypatch, tmp_path):
    doc = {"title": "Hello"}
    _run(doc, ["--target", "en", "--backend", "noop"], monkeypatch, tmp_path)
    cache_files = list(tmp_path.rglob("*.json"))
    assert cache_files, "cache should have written an entry"
