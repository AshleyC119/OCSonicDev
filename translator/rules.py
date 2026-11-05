"""Load and parse the supplier mapping table.

A row of ``yang2sonic_maptable`` is one mapping template.  The four data
columns are python-ish literals written by the supplier tool:

yang_key    ``//``-separated path pattern over the OC document
yang_value  a list of *selectors*, one per target
sonic_key   one ``//``-separated template, or a list of templates
sonic_value a list of candidate lists, aligned with sonic_key

Both key columns may be plain strings (not quoted) or python list literals, so
they are parsed leniently.
"""

from __future__ import annotations

import ast
import csv
import io
import re
from dataclasses import dataclass, field
from typing import Any, Optional

#: single-word directives that may appear inside a yang_value selector
DIRECTIVES = {
    "unchanged",
    "any",
    "NONE",
    "default",
    "compute",
    "combination",
    "string_combination",
    "list_combination",
    "list_value",
    "list_2_string",
    "empty_dict",
    "lowercase",
}

VAR_RE = re.compile(r"\$([A-Za-z0-9_\-]+)\$")


# ---------------------------------------------------------------------------
# lenient literal parsing
# ---------------------------------------------------------------------------
def parse_literal(text: str) -> Any:
    """Parse a CSV cell as a python literal, falling back to the raw text."""
    text = text.strip()
    if not text:
        return ""
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text


def parse_key_cell(text: str) -> list[str]:
    """Return the sonic_key cell as a list of templates."""
    text = (text or "").strip()
    if not text:
        return []
    if text[0] in "['":
        value = parse_literal(text)
        if isinstance(value, list):
            return [str(v) for v in value]
        if isinstance(value, str):
            return [value]
    return [text]


def split_path(template: str) -> list[str]:
    return [seg for seg in template.split("//")]


# ---------------------------------------------------------------------------
# selector model
# ---------------------------------------------------------------------------
@dataclass
class Selector:
    """One yang_value element.

    ``kind`` is one of
      ``directive``  a directive such as ``unchanged`` / ``compute``
      ``enum``       the OC value must be one of ``options``
      ``ockey``      the value comes from another OC path (``path``)
    ``branches`` is the candidate selection list for ``ockey`` selectors and
    for the ``[[spec], [branches]]`` form.
    """

    kind: str
    value: Any = None          # directive name, or list of enum options
    path: Optional[str] = None  # ockey path template
    branches: list[str] = field(default_factory=list)


def _parse_selector(element: Any) -> Selector:
    if not isinstance(element, list):
        return Selector("enum", [str(element)])

    inner = element[0] if element else None

    # [['ockey', path], [branches]] / [['ockey', path]]
    if isinstance(inner, list):
        spec = inner
        branches = element[1] if len(element) > 1 and isinstance(element[1], list) else []
        if spec and str(spec[0]) == "ockey":
            return Selector("ockey", None, str(spec[1]), [str(b) for b in branches])
        if len(spec) == 1 and str(spec[0]) in DIRECTIVES:
            return Selector("directive", str(spec[0]), branches=[str(b) for b in branches])
        return Selector("enum", [str(x) for x in spec], branches=[str(b) for b in branches])

    # ['ockey', path] (no branch list)
    if len(element) >= 2 and str(inner) == "ockey":
        return Selector("ockey", None, str(element[1]), ["ocvalue"])

    if len(element) == 1 and str(inner) in DIRECTIVES:
        return Selector("directive", str(inner))

    return Selector("enum", [str(x) for x in element])


# ---------------------------------------------------------------------------
# rule model
# ---------------------------------------------------------------------------
@dataclass
class Segment:
    """One compiled ``//`` segment of a yang_key pattern."""

    raw: str
    regex: re.Pattern
    vars: list[str]

    @property
    def literal_chars(self) -> int:
        return len(VAR_RE.sub("", self.raw))

    def match(self, text: str) -> Optional[dict[str, str]]:
        found = self.regex.fullmatch(text)
        if found is None:
            return None
        return {name: found.group(f"v{position}") for position, name in enumerate(self.vars)}


@dataclass
class Rule:
    index: int
    spine: str
    yang_key: str
    yang_value: str
    sonic_key: str
    sonic_value: str
    segments: list[Segment]
    selectors: list[Selector]
    sk_templates: list[str]
    sv_entries: list[list[Any]]

    # derived
    literal_chars: int = 0
    var_count: int = 0
    segments_len: int = 0

    @property
    def specificity(self) -> tuple[int, int, int]:
        return (self.literal_chars, -self.var_count, self.segments_len)

    @property
    def is_suppression(self) -> bool:
        return len(self.selectors) == 1 and self.selectors[0].kind == "directive" \
            and self.selectors[0].value == "NONE"

    def match(self, segments: list[str]) -> Optional[dict[str, str]]:
        """Match the pattern against flattened OC path segments."""
        if len(segments) != len(self.segments):
            return None
        bindings: dict[str, str] = {}
        for pattern, text in zip(self.segments, segments):
            found = pattern.match(text)
            if found is None:
                return None
            for name, value in found.items():
                previous = bindings.get(name)
                if previous is not None and previous != value:
                    return None
                bindings[name] = value
        return bindings


def _compile_segment(raw: str) -> Segment:
    names: list[str] = []
    pieces: list[str] = []
    position = 0
    for found in VAR_RE.finditer(raw):
        pieces.append(re.escape(raw[position:found.start()]))
        names.append(found.group(1))
        # greedy: the last placeholder in a segment absorbs the remainder
        pieces.append(f"(?P<v{len(names) - 1}>.*)")
        position = found.end()
    pieces.append(re.escape(raw[position:]))
    regex = re.compile("".join(pieces), re.DOTALL)
    return Segment(raw=raw, regex=regex, vars=names)


def _parse_sv(entry: Any) -> list[Any]:
    """Normalise one sonic_value entry to a list of candidates."""
    if isinstance(entry, list):
        return entry
    return [entry]


def load_rules(csv_path: str) -> list[Rule]:
    with open(csv_path, "rb") as handle:
        raw = handle.read()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rules: list[Rule] = []
    for index, row in enumerate(reader):
        yang_key = (row.get("yang_key") or "").strip()
        if not yang_key:
            continue
        yang_value_raw = row.get("yang_value") or ""
        yv = parse_literal(yang_value_raw)
        if not isinstance(yv, list):
            yv = [yv]
        selectors = [_parse_selector(element) for element in yv]

        sk_templates = parse_key_cell(row.get("sonic_key") or "")
        sv = parse_literal(row.get("sonic_value") or "[]")
        if not isinstance(sv, list):
            sv = [sv]
        sv_entries = [_parse_sv(entry) for entry in sv]

        # Multi-target rows wrap each target's candidate list one extra level
        # (``[[['a','b']], [['c']]]``); single-target rows do not.
        if len(sk_templates) > 1:
            unwrapped: list[list[Any]] = []
            for entry in sv_entries:
                if len(entry) == 1 and isinstance(entry[0], list):
                    unwrapped.append(entry[0])
                else:
                    unwrapped.append(entry)
            sv_entries = unwrapped

        # Some rows write a *single* ``[spec, branches]`` selector at the top
        # level even for a single target (e.g. ``[['ockey', p], ['ocvalue']]``).
        if len(selectors) != len(sk_templates) and len(sk_templates) == 1:
            merged = _parse_selector(yv)
            if merged.kind in ("ockey", "directive", "enum"):
                selectors = [merged]

        segments = [_compile_segment(seg) for seg in split_path(yang_key)]
        rule = Rule(
            index=index,
            spine=(row.get("spine") or "").strip(),
            yang_key=yang_key,
            yang_value=yang_value_raw,
            sonic_key=row.get("sonic_key") or "",
            sonic_value=row.get("sonic_value") or "",
            segments=segments,
            selectors=selectors,
            sk_templates=sk_templates,
            sv_entries=sv_entries,
        )
        rule.literal_chars = sum(seg.literal_chars for seg in segments)
        rule.var_count = sum(len(seg.vars) for seg in segments)
        rule.segments_len = len(segments)
        rules.append(rule)
    return rules
