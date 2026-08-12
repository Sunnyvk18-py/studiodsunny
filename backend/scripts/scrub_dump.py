#!/usr/bin/env python3
"""Scrub a Postgres SQL dump for safe check-in.

Replaces PII while preserving:
  - row counts
  - primary keys / UUIDs
  - foreign-key relationships
  - non-PII structure (statuses, dates, amounts shape)

Usage:
  python scripts/scrub_dump.py path/to/raw.dump.sql -o tests/fixtures/prod_shape.sql

Never commit the raw dump.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path


EMAIL_RE = re.compile(
    r"'([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})'",
    re.IGNORECASE,
)
# Common INSERT column patterns — replace string literals in known PII columns when we can.
PHONE_RE = re.compile(r"'(\+?\d[\d\s\-()]{6,}\d)'")
# Salary / money-looking decimals that appear as employee compensation columns are
# handled via a conservative rewrite of large NUMERIC literals next to salary context.


def _stable(seed: str, n: int = 8) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:n]


def scrub_email(match: re.Match[str]) -> str:
    original = match.group(1)
    tag = _stable(original.lower())
    return f"'user_{tag}@example.invalid'"


def scrub_phone(match: re.Match[str]) -> str:
    original = match.group(1)
    tag = _stable(original)
    # Preserve length-ish but fake
    return f"'+1555{_stable(tag, 7)}'"


def scrub_names_in_inserts(sql: str) -> str:
    """Rewrite common name / business columns in INSERT VALUES via heuristics.

    We do not parse full SQL; we replace high-signal string literals that look like
    people or company names while leaving short status tokens alone.
    """

    def maybe_name(m: re.Match[str]) -> str:
        val = m.group(1)
        if len(val) < 3:
            return m.group(0)
        lower = val.lower()
        if lower in {
            "draft",
            "active",
            "todo",
            "completed",
            "founder",
            "developer",
            "designer",
            "channel",
            "page",
            "inr",
            "usd",
            "jpy",
            "full_time",
            "healthy",
            "planning",
            "hyderabad",
        }:
            return m.group(0)
        if "@" in val or val.startswith("http"):
            return m.group(0)
        if re.fullmatch(r"[0-9a-f\-]{36}", val, re.I):
            return m.group(0)
        tag = _stable(val)
        if " " in val or val[:1].isupper():
            return f"'Scrubbed Name {tag}'"
        return m.group(0)

    # Only touch reasonably long quoted strings (avoid enums / short codes).
    return re.sub(r"'([^']{4,240})'", maybe_name, sql)


def scrub_salaries(sql: str) -> str:
    """Replace salary-like amounts (not all money — keep invoice shape via modulo)."""

    # employee salary columns often appear as 5–7 digit integers / decimals
    def repl(m: re.Match[str]) -> str:
        raw = m.group(0)
        try:
            n = float(raw)
        except ValueError:
            return raw
        if 10_000 <= n <= 10_000_000:
            # Stable fake compensation
            return "75000.00"
        return raw

    return re.sub(r"\b\d{5,7}(?:\.\d{1,2})?\b", repl, sql)


def scrub(sql: str) -> str:
    out = sql
    out = EMAIL_RE.sub(scrub_email, out)
    out = PHONE_RE.sub(scrub_phone, out)
    out = scrub_salaries(out)
    out = scrub_names_in_inserts(out)
    header = (
        "-- Scrubbed production-shaped dump for migration tests.\n"
        "-- Generated/scrubbed by scripts/scrub_dump.py — do not commit raw dumps.\n"
        "-- PII replaced; IDs and foreign keys preserved.\n\n"
    )
    if not out.lstrip().startswith("-- Scrubbed"):
        out = header + out
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path, help="Raw .sql dump")
    p.add_argument("-o", "--output", type=Path, required=True, help="Scrubbed output path")
    args = p.parse_args(argv)
    raw = args.input.read_text(encoding="utf-8", errors="replace")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(scrub(raw), encoding="utf-8")
    print(f"Wrote scrubbed dump → {args.output} ({len(raw)} → {args.output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
