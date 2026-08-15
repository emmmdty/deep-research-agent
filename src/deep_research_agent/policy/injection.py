"""Prompt-injection guardrails for untrusted retrieved content.

Deep research agents read arbitrary web pages and search snippets; an attacker
can plant instruction-like text ("ignore previous instructions and ...") that
the model may treat as a command. This module implements defense in depth:

1. **Pattern scan** — known instruction-override and jailbreak patterns with
   severity ratings.
2. **Line quarantine** — lines carrying high-severity directives are removed
   from the content the model ever sees (fail closed per source).
3. **Token neutralization** — chat-format tokens (``<|im_start|>``, ``[INST]``,
   ``### Human:``) are escaped so they are inert text, not delimiters.
4. **Data fence** — every source is wrapped in ``<source_data>`` fences; the
   agent system prompts instruct the model that fenced content is untrusted
   data, never instructions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_SOURCE_FENCE_START = "<source_data>"
_SOURCE_FENCE_END = "</source_data>"

_SEVERITIES = ("high", "medium", "low")

# (regex, severity, label)
_INJECTION_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    # instruction-override attempts (high: quarantine the whole line)
    (
        re.compile(
            r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|"
            r"messages?|context|rules)",
            re.IGNORECASE,
        ),
        "high",
        "ignore_previous_instructions",
    ),
    (
        re.compile(
            r"disregard\s+(?:(?:any|all)\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|"
            r"messages?|context|rules)",
            re.IGNORECASE,
        ),
        "high",
        "disregard_instructions",
    ),
    (
        re.compile(
            r"do\s+not\s+follow\s+(?:your\s+)?(?:previous|prior|the)\s+(?:instructions?|prompts?|system\s+prompt)",
            re.IGNORECASE,
        ),
        "high",
        "do_not_follow",
    ),
    (
        re.compile(
            r"override\s+(your|all\s+(previous|prior))\s+(instructions?|prompts?|system)",
            re.IGNORECASE,
        ),
        "high",
        "override_instructions",
    ),
    (
        re.compile(
            r"forget\s+(all\s+)?(your|previous)\s+(instructions?|prompts?|rules)", re.IGNORECASE
        ),
        "high",
        "forget_instructions",
    ),
    (
        re.compile(
            r"you\s+are\s+now\s+(?:the\s+)?(?:an?\s+|a\s+)?[\w-]+(?:\s+[\w-]+){0,2}\s+(?:assistant|agent|system)",
            re.IGNORECASE,
        ),
        "high",
        "role_override",
    ),
    (re.compile(r"from\s+now\s+on,\s+you\s+(are|will)", re.IGNORECASE), "high", "role_override"),
    (re.compile(r"your\s+system\s+prompt", re.IGNORECASE), "high", "system_prompt_reference"),
    (
        re.compile(r"(reveal|print|show|output)\s+(your\s+)?(system\s+)?prompt", re.IGNORECASE),
        "high",
        "prompt_leak_attempt",
    ),
    (re.compile(r"jailbreak", re.IGNORECASE), "high", "jailbreak"),
    (
        re.compile(
            r"secretly\s+(?:change|set|switch)\s+(?:your\s+)?(?:mode|behavior|instructions)",
            re.IGNORECASE,
        ),
        "high",
        "stealth_override",
    ),
    # chat-format delimiter tokens (medium: neutralize)
    (
        re.compile(r"<\|(?:im_start|im_end|system|user|assistant|tool)\|>"),
        "medium",
        "chat_delimiter_token",
    ),
    (re.compile(r"\[/?(?:INST|SYS)\]"), "medium", "llama_chat_token"),
    (
        re.compile(r"^#{0,3}\s*(human|assistant|system)\s*:", re.IGNORECASE | re.MULTILINE),
        "medium",
        "chat_header_line",
    ),
    (
        re.compile(r"<system[_\- ]?(message|instructions?)>", re.IGNORECASE),
        "medium",
        "html_system_tag",
    ),
    (
        re.compile(r"&lt;\|im_start\|&gt;|&#124;im_start&#124;", re.IGNORECASE),
        "medium",
        "html_encoded_delimiter",
    ),
    (re.compile(r"---\s*instructions?\s*---", re.IGNORECASE), "medium", "instruction_fence"),
    (
        re.compile(r"<\s*(?:instructions?|prompt|system)[^>]*>", re.IGNORECASE),
        "medium",
        "instruction_tag",
    ),
)

_MEDIUM_TOKEN_NEUTRALIZE: tuple[tuple[str, str], ...] = (
    ("<|im_start|>", "<\\|im_start\\|>"),
    ("<|im_end|>", "<\\|im_end\\|>"),
    ("<|system|>", "<\\|system\\|>"),
    ("<|user|>", "<\\|user\\|>"),
    ("<|assistant|>", "<\\|assistant\\|>"),
    ("<|tool|>", "<\\|tool\\|>"),
    ("[INST]", "[\\INST]"),
    ("[/INST]", "[\\/INST]"),
    ("[SYS]", "[\\SYS]"),
)


@dataclass(frozen=True)
class InjectionFinding:
    """One detected injection pattern in untrusted content."""

    pattern: str
    severity: str
    line_number: int
    context: str = field(default="")

    @property
    def quarantinable(self) -> bool:
        return self.severity == "high"


@dataclass(frozen=True)
class SanitizedContent:
    """Content after injection sanitization."""

    text: str
    findings: tuple[InjectionFinding, ...] = ()
    quarantined_lines: int = 0
    quarantined_chars: int = 0

    @property
    def flagged(self) -> bool:
        return bool(self.findings)


def scan_injection(text: str) -> list[InjectionFinding]:
    """Scan untrusted text for injection patterns.

    Returns one finding per (pattern, line) match; a line containing several
    patterns yields several findings.
    """

    findings: list[InjectionFinding] = []
    if not text:
        return findings
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern, severity, label in _INJECTION_PATTERNS:
            if pattern.search(line):
                findings.append(
                    InjectionFinding(
                        pattern=label,
                        severity=severity,
                        line_number=line_number,
                        context=line.strip()[:160],
                    )
                )
    return findings


def sanitize_content(text: str) -> SanitizedContent:
    """Sanitize untrusted text for inclusion in a model prompt.

    High-severity lines are quarantined (removed). Medium-severity delimiter
    tokens are neutralized in the surviving text. Low-severity patterns are
    only reported, never modified.
    """

    findings = scan_injection(text)
    if not findings:
        return SanitizedContent(text=text)
    surviving: list[str] = []
    quarantined = 0
    quarantined_chars = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        if any(
            finding.severity == "high" and finding.line_number == line_number
            for finding in findings
        ):
            quarantined += 1
            quarantined_chars += len(line)
            continue
        surviving.append(line)
    sanitized = "\n".join(surviving)
    for token, replacement in _MEDIUM_TOKEN_NEUTRALIZE:
        sanitized = sanitized.replace(token, replacement)
    return SanitizedContent(
        text=sanitized,
        findings=tuple(findings),
        quarantined_lines=quarantined,
        quarantined_chars=quarantined_chars,
    )


def should_quarantine_source(text: str) -> bool:
    """True when a source attempts an instruction override (fail closed)."""

    return any(finding.severity == "high" for finding in scan_injection(text))


def fence_content(text: str) -> str:
    """Wrap content in the untrusted-data fence markers."""

    return f"{_SOURCE_FENCE_START}\n{text}\n{_SOURCE_FENCE_END}"


__all__ = [
    "InjectionFinding",
    "SanitizedContent",
    "fence_content",
    "sanitize_content",
    "scan_injection",
    "should_quarantine_source",
]
