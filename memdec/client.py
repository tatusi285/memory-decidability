"""OpenAI-compatible chat client with retries, plus a deterministic offline stand-in.

The network client exists so that the study can be re-run; the offline responder
exists so that the *pipeline* can be tested in CI with no key and no cost.  The
offline responder is a simulator of the positional rule the study discovered, not a
model, and every artifact produced with it records ``"simulated": true``.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_KEY_ENVS = ("MEMDEC_API_KEY", "PILOT_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY")
RETRYABLE = (429, 500, 502, 503, 504)


def find_api_key(env_names: str | tuple[str, ...] = DEFAULT_KEY_ENVS) -> tuple[str, str]:
    """Return ``(key, env_name)`` from the first populated environment variable."""
    names = (env_names,) if isinstance(env_names, str) else env_names
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value, name
    return "", ""


@dataclass
class ChatClient:
    """Minimal chat-completions client; no third-party HTTP dependency."""

    model: str
    base_url: str
    api_key: str
    max_tokens: int = 24
    temperature: float = 0.0
    timeout: float = 60.0
    retries: int = 4

    def ask(self, prompt: str) -> tuple[str, dict]:
        """Return ``(answer, metadata)``; failures become a string, never an exception.

        A single failed call must not invalidate a whole run, so errors are captured
        as ``<error:...>`` and scored ``unknown``.  That choice is why the paper's
        ``unknown`` bucket exists at all; it is only 0.26% of all probes.
        """
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        request = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Connection": "close",
            },
            method="POST",
        )
        last_error = ""
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                content = (payload["choices"][0]["message"]["content"] or "").strip()
                return content, {"attempts": attempt + 1, "status": "ok",
                                 "id": payload.get("id", "")}
            except urllib.error.HTTPError as exc:
                last_error = f"HTTP{exc.code}"
                if exc.code in RETRYABLE and attempt < self.retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return f"<error:{last_error}>", {"attempts": attempt + 1, "status": last_error}
            except Exception as exc:  # noqa: BLE001 - network faults are data, not crashes
                last_error = type(exc).__name__
                if attempt < self.retries - 1:
                    time.sleep(1.0 * (attempt + 1))
                    continue
        return f"<error:{last_error}>", {"attempts": self.retries, "status": last_error}


class RuleSimulator:
    """Deterministic stand-in for the model, used by tests and ``--offline``.

    It answers with the value of the last record in the context, which is the rule
    the study found for both DeepSeek models.  It is *not* a model and its output is
    *not* evidence: it exists so that the plumbing (context assembly, scoring,
    aggregation, table generation) can be exercised offline and so that the
    determinism claims in ``docs/REVIEW.md`` can be illustrated end to end.
    """

    name = "rule-simulator/last-record"

    def __init__(self) -> None:
        self.calls = 0

    def ask(self, prompt: str) -> tuple[str, dict]:
        self.calls += 1
        record_lines = [
            line for line in prompt.splitlines()
            if line.startswith("[") or ("·" in line) or ("。" in line and "问题" not in line)
        ]
        for line in reversed(record_lines):
            for token in line.replace("=", " ").replace("，", " ").replace("。", " ").split():
                candidate = token.strip("[]()（）:：,，.")
                if candidate.isdigit() and len(candidate) >= 4:
                    return candidate, {"attempts": 1, "status": "simulated"}
        return "unknown", {"attempts": 1, "status": "simulated"}
