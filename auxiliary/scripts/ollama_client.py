#!/usr/bin/env python3
"""Minimal local-Ollama HTTP client, shared by every LLM-proposer tier in
this project. Talks to a local Ollama server by default -- no API key, no
per-call cost, nothing to add as a repository secret.

Extracted from the retired LLM promotion-evidence pilot script (moved to
trash/scripts/propose_promotion_evidence.py) so scripts/
llm_propose_clause_structure.py (the tower pipeline's third tree-source
tier) keeps a real caller for this code without depending on trashed,
pilot-specific logic.
"""

from __future__ import annotations

import json
import urllib.request

DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_ENDPOINT = "http://localhost:11434/api/generate"


def query_ollama(
    prompt: str,
    model: str = DEFAULT_MODEL,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: float = 60.0,
) -> dict:
    payload = json.dumps(
        {"model": model, "prompt": prompt, "format": "json", "stream": False}
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    return json.loads(body["response"])
