"""Diff the translator's emission list against a hand-derived audit file.

Both sides use the contract notation::

    TABLE|KEY|FIELD = <json value>  # optional comment

The comparison is semantic on ``(table, key, field, value)``; ordering and
comments are ignored.  Usage::

    python tools/audit_diff.py audit/netinst.expected.txt
    python tools/audit_diff.py audit/*.expected.txt --details outputs/translate_details.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DETAILS = ROOT / "outputs" / "translate_details.txt"


def parse_line(line: str):
    text = line.split("  # ", 1)[0].strip()
    if not text or text.startswith("#"):
        return None
    if " = " not in text:
        raise ValueError(f"cannot parse audit line: {line!r}")
    lhs, rhs = text.split(" = ", 1)
    parts = lhs.split("|")
    table = parts[0]
    key = parts[1] if len(parts) > 1 else ""
    field_name = "|".join(parts[2:]) if len(parts) > 2 else ""
    try:
        value = json.loads(rhs)
    except json.JSONDecodeError:
        value = rhs
    return (table, key, field_name, json.dumps(value, sort_keys=True))


def load(path: Path) -> set:
    entries = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = parse_line(line)
        if parsed:
            entries.add(parsed)
    return entries


ROW_RE = __import__("re").compile(r"#.*?(?:\brow[=\s]+(\d+)|\br(\d+)\b)")


def _row_of(line: str) -> int | None:
    found = ROW_RE.search(line)
    if not found:
        return None
    return int(found.group(1) or found.group(2))


def load_with_rows(path: Path) -> tuple[set, set]:
    """Return ``(entries, rule_row_indexes)`` for an audit file."""
    entries = set()
    rows: set[int] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = parse_line(line)
        if parsed:
            entries.add(parsed)
        row = _row_of(line)
        if row is not None:
            rows.add(row)
    return entries, rows


def load_engine(path: Path) -> dict[int, set]:
    """Index engine detail lines by the rule row that produced them."""
    by_rule: dict[int, set] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = parse_line(line)
        if not parsed:
            continue
        marker = line.rsplit("# rule ", 1)
        rule_index = int(marker[1].split()[0]) if len(marker) == 2 else -1
        by_rule.setdefault(rule_index, set()).add(parsed)
    return by_rule


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("audits", nargs="+", help="expected-output files")
    parser.add_argument("--details", default=str(DEFAULT_DETAILS))
    parser.add_argument(
        "--by-rule-rows",
        action="store_true",
        help="compare restricted to the rule rows named in the audit comments",
    )
    parser.add_argument(
        "--only-tables",
        action="store_true",
        help="when reporting engine-only lines, restrict to tables named by the audit",
    )
    args = parser.parse_args(argv)

    engine = load(Path(args.details))
    by_rule = load_engine(Path(args.details))
    status = 0
    for audit_path in args.audits:
        if args.by_rule_rows:
            audit, rows = load_with_rows(Path(audit_path))
            scoped: set = set()
            for rule_index in rows:
                scoped |= by_rule.get(rule_index, set())
            missing = sorted(audit - scoped)
            extra = sorted(scoped - audit)
            # a hand audit lists the *final* value per field, the engine details
            # list every write; separate those bookkeeping differences out
            audits_by_field = {(e[0], e[1], e[2]) for e in audit}
            really_missing = [e for e in missing if e not in engine]
            provenance_only = [e for e in missing if e in engine]
            overwritten = [e for e in extra if (e[0], e[1], e[2]) in audits_by_field]
            really_extra = [e for e in extra if (e[0], e[1], e[2]) not in audits_by_field]
            missing, extra = really_missing, really_extra
            if provenance_only or overwritten:
                print(
                    f"   (bookkeeping: {len(provenance_only)} entries present under a different"
                    f" rule row, {len(overwritten)} raw writes later overwritten by the audit's"
                    " final value)"
                )
            label = f"{len(rows)} rule rows"
        else:
            audit = load(Path(audit_path))
            tables = {entry[0] for entry in audit}
            missing = sorted(audit - engine)
            extra = sorted(
                entry
                for entry in (engine - audit)
                if not args.only_tables or entry[0] in tables
            )
            label = f"{len(audit)} expected"
        print(f"== {audit_path}: {label}, {len(missing)} missing, {len(extra)} extra")
        for entry in missing[:40]:
            print(f"  MISSING  {entry[0]}|{entry[1]}|{entry[2]} = {entry[3]}")
        for entry in extra[:40]:
            print(f"  EXTRA    {entry[0]}|{entry[1]}|{entry[2]} = {entry[3]}")
        if missing or extra:
            status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())

