"""Value DSL evaluation.

The ``yang_value`` / ``sonic_value`` columns encode a small expression language:

* selectors choose which candidate of ``sonic_value`` applies;
* candidates are templates over the match bindings (``$VAR$``, bare names such
  as ``INTERFACE``), can be concatenations written with ``+``, can be foreign
  key references (``[TABLE|KEY]``), inline lookups (``{|ockey=path}``) or
  transforms of the OC value (``original//1000``, ``10000-original``,
  ``log2(original)``, ``lowercase``).
"""

from __future__ import annotations

import math
import re
from typing import Any, Optional

from .rules import VAR_RE, Selector

OMIT = object()      # "do not emit this field"
EMPTY_DICT = object()  # "emit the key with an empty object value"

_BRACKET = re.compile(r"^\[(?P<inner>.*)\]$", re.DOTALL)
_INLINE_OCKEY = re.compile(r"\{\|ockey=(?P<path>[^}]*)\}")
_ORIGINAL_DIV = re.compile(r"^original//(\d+)$")
_NUM_MINUS_ORIGINAL = re.compile(r"^(\d+)-original$")
_LOG2_ORIGINAL = re.compile(r"^log2\(original\)$")

#: bare (unquoted) provider variables that may appear in a candidate template
KNOWN_VARS = {
    "INTERFACE", "INTERFACEID", "SUBINTERFACE", "ADDRESS", "IPVERSION",
    "VALUE", "VALUE_LIST", "GROUP", "SERVER", "QUEUEID", "SET", "IP", "MASK",
    "RANGE", "PREFIX", "COMMUNITY", "NEIGHBOR", "AREA", "NAME", "ASIC", "PORT",
    "TYPE", "ACL-SET", "DEFINITION", "STATEMENT", "ZEBRA", "RULE", "SCHEDULER",
    "POLICY", "COMPONENT", "NETWORK", "HOP", "IPADDR", "IPMASK", "PG-NUM",
    "QINDEX", "PBR-NAME", "NEXTHOP", "INTF-NAME", "RULE-ID", "VRF",
    "TARGET-VRF", "SOURCE-VRF", "TUNNEL", "PORTS", "PROTOCOL", "NEXTHOP-ID",
    "INTERFACE-NAME", "VLAN", "SESSION", "SOURCE", "TARGET", "PROFILE",
}

_TRANSFORM_STATIC = {
    "unchanged": "_value",
    "value": "_value",
    "VALUE": "_value",
    "ocvalue": "_ocvalue",
    "value_list": "_value_list_item",
    "VALUE_LIST": "_value_list_item",
    # row 68 writes the BMC gateway as the type token ``ip``: the value is an
    # address that is copied verbatim (the alternative reading would emit the
    # literal string "ip" as a gateway).
    "ip": "_value",
}

#: lone selector tokens that act as a type marker rather than a value to match
PASS_THROUGH_TOKENS = {"ip"}


class ValueEngine:
    """Renders templates against a match context and facilitates lookups."""

    def __init__(self, doc):
        self.doc = doc
        self.warnings: list[str] = []

    # ------------------------------------------------------------------
    # lookups
    # ------------------------------------------------------------------
    def lookup(self, path_template: str, ctx: dict[str, Any]) -> Optional[str]:
        """Resolve an ``ockey`` path against the OC document.

        Placeholders already bound in ``ctx`` are substituted; remaining
        placeholders act as wildcards.
        """
        resolved = VAR_RE.sub(
            lambda m: str(ctx.get(m.group(1), m.group(0))),
            path_template,
        )
        segments = resolved.split("//")
        patterns = []
        for segment in segments:
            pieces = []
            position = 0
            for found in VAR_RE.finditer(segment):
                pieces.append(re.escape(segment[position:found.start()]))
                pieces.append(".*")
                position = found.end()
            pieces.append(re.escape(segment[position:]))
            patterns.append(re.compile("".join(pieces), re.DOTALL))
        for leaf in self.doc.leaves:
            if len(leaf.segments) != len(patterns):
                continue
            if all(p.fullmatch(s) for p, s in zip(patterns, leaf.segments)):
                return leaf.text()
        return None

    # ------------------------------------------------------------------
    # list helpers
    # ------------------------------------------------------------------
    @staticmethod
    def parse_vlan_list(text: str) -> list[str]:
        """Expand ``2,10-12`` into ``['2','10','11','12']``."""
        items: list[str] = []
        for chunk in str(text).split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "-" in chunk:
                try:
                    start, end = chunk.split("-", 1)
                    items.extend(str(n) for n in range(int(start), int(end) + 1))
                    continue
                except ValueError:
                    pass
            items.append(chunk)
        return items

    @staticmethod
    def listify(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]

    # ------------------------------------------------------------------
    # template rendering
    # ------------------------------------------------------------------
    def render(self, template: Any, ctx: dict[str, Any]) -> Any:
        if not isinstance(template, str):
            return template
        text = template

        if text == "NONE":
            return OMIT
        if text == "empty_dict":
            return EMPTY_DICT
        if text in ("unchanged", "value", "VALUE"):
            raw = ctx.get("_raw_value")
            if isinstance(raw, list):
                return list(raw)
            return ctx.get("_value")
        if text in _TRANSFORM_STATIC:
            return ctx.get(_TRANSFORM_STATIC[text], ctx.get("_value"))
        if text == "list_value":
            return self.listify(ctx.get("_value"))
        if text == "list_2_string":
            return ",".join(self.listify(ctx.get("_value")))
        if text == "lowercase":
            return str(ctx.get("_value", "")).lower()

        # whole-value transforms
        found = _ORIGINAL_DIV.match(text)
        if found:
            return str(_as_int(ctx.get("_value")) // int(found.group(1)))
        found = _NUM_MINUS_ORIGINAL.match(text)
        if found:
            return str(int(found.group(1)) - _as_int(ctx.get("_value")))
        found = _LOG2_ORIGINAL.match(text)
        if found:
            return _log2(ctx.get("_value"))

        # foreign key reference / bracketed expression
        bracket = _BRACKET.match(text)
        if bracket:
            inner = bracket.group("inner")
            if inner.startswith("+") and inner.endswith("+") and len(inner) > 1:
                return self.render(inner.strip("+"), ctx)
            if "|" in inner:
                return self.render(inner.split("|", 1)[1], ctx)
            return self.render(inner, ctx)

        # inline conditional key suffix: {|ockey=path}
        if "{|ockey=" in text:
            def replace(match: "re.Match[str]") -> str:
                looked = self.lookup(match.group("path"), ctx)
                return "" if not looked else "|" + looked

            text = _INLINE_OCKEY.sub(replace, text)
            if not text:
                return OMIT

        # variable substitution (placeholders first, then bare names)
        text = VAR_RE.sub(lambda m: self._resolve(m.group(1), ctx), text)

        # concatenation with '+' when at least one part is a variable
        if "+" in text:
            parts = text.split("+")
            names = [part for part in parts if self._is_variable(part, ctx)]
            if names:
                rendered = []
                for part in parts:
                    if self._is_variable(part, ctx):
                        rendered.append(self._resolve(part, ctx))
                    else:
                        rendered.append(part)
                return "".join(rendered)

        if self._is_variable(text, ctx):
            return self._resolve(text, ctx)

        # keep unknown bare tokens literal; only known provider variables warn
        if text in KNOWN_VARS:
            message = f"unbound variable {text!r} kept literally"
            if message not in self.warnings:
                self.warnings.append(message)
        return text

    # ------------------------------------------------------------------
    # key segments
    # ------------------------------------------------------------------
    def render_segment(self, template: str, ctx: dict[str, Any]) -> str:
        """Render one ``//`` segment of a sonic_key template.

        Key segments are identifiers, not values: only ``$VAR$`` placeholders
        and the inline ``{|ockey=path}`` suffix are substituted.  Bare tokens
        are literal key names — ``BMC//INTERFACE//defgw`` keeps ``INTERFACE``,
        and a field literally named ``ip`` (``DNS//server//ip``) stays ``ip``.
        """
        text = template
        if "{|ockey=" in text:
            def replace(match: "re.Match[str]") -> str:
                looked = self.lookup(match.group("path"), ctx)
                return "" if not looked else "|" + looked

            text = _INLINE_OCKEY.sub(replace, text)
            if not text:
                return ""
        return VAR_RE.sub(lambda m: self._resolve(m.group(1), ctx), text)

    def _is_variable(self, part: str, ctx: dict[str, Any]) -> bool:
        if part in ctx:
            return True
        return part in ("value", "ocvalue", "value_list", "original")

    def _resolve(self, name: str, ctx: dict[str, Any]) -> str:
        if name in ctx:
            value = ctx[name]
            if isinstance(value, list):
                return ",".join(str(item) for item in value)
            return "" if value is None else str(value)
        if name in ("value", "VALUE"):
            return str(ctx.get("_value", ""))
        if name in ("ocvalue", "OCVALUE"):
            return str(ctx.get("_ocvalue", "") or "")
        if name in ("value_list", "VALUE_LIST"):
            return str(ctx.get("_value_list_item", ""))
        if name in KNOWN_VARS:
            message = f"unbound variable {name!r} rendered empty"
            if message not in self.warnings:
                self.warnings.append(message)
            return ""
        return "$" + name + "$"


def _as_int(value: Any) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        try:
            return int(float(str(value).strip()))
        except (TypeError, ValueError):
            return 0


def _as_number(value: Any) -> float:
    """Parse an integer, decimal or ``a/b`` fraction as a float."""
    text = str(value).strip()
    if "/" in text:
        numerator, _, denominator = text.partition("/")
        try:
            return float(numerator) / float(denominator)
        except (TypeError, ValueError, ZeroDivisionError):
            return 0.0
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def _log2(value: Any) -> str:
    """``log2(original)`` for byte counts *and* buffer fractions (1/8 -> -3)."""
    number = _as_number(value)
    if number <= 0:
        return "0"
    return str(int(round(math.log2(number))))


def resolve_candidate(candidates: list[Any], index: int) -> Any:
    if not candidates:
        return OMIT
    if index < 0:
        index = 0
    if index >= len(candidates):
        index = len(candidates) - 1
    return candidates[index]


def selector_index(selector: Selector, ctx: dict[str, Any], engine: ValueEngine) -> Optional[int]:
    """Return the sonic_value candidate index for one selector, or ``None``."""
    if selector.kind == "directive":
        return 0
    if selector.kind == "enum":
        value = ctx.get("_value")
        options = [str(option) for option in (selector.value or [])]
        if isinstance(value, list):
            value = ",".join(str(item) for item in value)
        if value is None:
            value = ""
        value = str(value)
        if value in options:
            return options.index(value)
        # a lone type token (e.g. ``[['ip']]``) means "copy the addressed value"
        if len(options) == 1 and options[0] in PASS_THROUGH_TOKENS:
            return 0
        return None
    if selector.kind == "ockey":
        looked = engine.lookup(selector.path or "", ctx)
        ctx["_ocvalue"] = looked
        branches = selector.branches or ["ocvalue"]
        if branches and branches[0] in ("ocvalue", "combination_ocvalue"):
            return 0
        if looked is not None and looked in branches:
            return branches.index(looked)
        if "ockey_default" in branches:
            return branches.index("ockey_default")
        return 0
    return 0
