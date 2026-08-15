"""Optional Aho-Corasick batch matching for verbatim quote containment.

``pyahocorasick`` is an optional accelerator: when it is not installed the
matcher builders return ``None`` and callers keep the plain substring path, so
behavior is bit-identical with or without the package. The package renames its
importable module between major versions (``pyahocorasick`` in 1.x,
``ahocorasick`` in 2.x), so both names are probed.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def build_verbatim_matcher(texts: Iterable[str]) -> Any:
    """Build an Aho-Corasick automaton over ``texts`` (quote patterns).

    Returns ``None`` when ``pyahocorasick`` is unavailable so callers can fall
    back to plain substring containment. Empty patterns are skipped: an empty
    string is a substring of every text, so ``match_quotes`` treats it as
    always contained without an automaton entry.
    """

    try:
        import pyahocorasick as _automaton_module
    except ImportError:
        try:
            import ahocorasick as _automaton_module
        except ImportError:
            return None
    automaton = _automaton_module.Automaton()
    for text in texts:
        if text:
            automaton.add_word(text, text)
    automaton.make_automaton()
    return automaton


def match_quotes(matcher: Any, spans, text: str) -> dict[Any, bool]:
    """Batch ``quote in text`` containment checks for ``(span_id, quote)`` pairs.

    Results mirror plain substring semantics exactly: a quote is contained when
    the automaton reports a match in ``text`` (and an empty quote is always
    contained). ``matcher`` may be ``None``, in which case every quote is
    checked with the plain ``in`` operator — identical results, no index.
    """

    results: dict[Any, bool] = {}
    pending: list[tuple[Any, str]] = []
    for span_id, quote in spans:
        quote = str(quote)
        results[span_id] = not quote
        if quote:
            pending.append((span_id, quote))
    if not pending:
        return results
    if matcher is None:
        for span_id, quote in pending:
            results[span_id] = quote in text
        return results
    found = {value for _, value in matcher.iter(text)}
    for span_id, quote in pending:
        results[span_id] = quote in found
    return results
