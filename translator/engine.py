"""Rule matching and SONiC configuration emission."""

from __future__ import annotations

import collections
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .ocdoc import Leaf, OcDocument
from .rules import Rule, VAR_RE, split_path
from .values import EMPTY_DICT, OMIT, ValueEngine, resolve_candidate, selector_index

_INLINE_OCKEY = re.compile(r"\{\|ockey=(?P<path>[^}]*)\}")


@dataclass
class Emission:
    table: str
    key: str
    field: Optional[str]
    value: Any
    rule_index: int
    oc_path: str

    def render_line(self) -> str:
        import json

        if self.field is None:
            return f"{self.table}|{self.key} = {json.dumps(self.value, ensure_ascii=False)}"
        return (
            f"{self.table}|{self.key}|{self.field} = "
            f"{json.dumps(self.value, ensure_ascii=False)}"
        )


@dataclass
class TranslationReport:
    emissions: list[Emission] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rule_fires: dict[int, int] = field(default_factory=dict)
    suppressed_leaves: list[str] = field(default_factory=list)
    unmatched_leaves: list[str] = field(default_factory=list)
    matched_leaves: int = 0
    total_leaves: int = 0

    def summary(self) -> dict[str, Any]:
        tables = collections.Counter(e.table for e in self.emissions)
        return {
            "leaves": self.total_leaves,
            "matched_leaves": self.matched_leaves,
            "unmatched_leaves": len(self.unmatched_leaves),
            "suppressed_leaves": len(self.suppressed_leaves),
            "emissions": len(self.emissions),
            "rules_fired": len(self.rule_fires),
            "tables": dict(tables),
        }


class Translator:
    """Applies the mapping table to one OC document."""

    def __init__(self, rules: list[Rule], doc: OcDocument):
        self.rules = rules
        self.doc = doc
        self.values = ValueEngine(doc)
        self.report = TranslationReport()
        self._warned: set[str] = set()

    # ------------------------------------------------------------------
    # matching
    # ------------------------------------------------------------------
    def _index_rules(self) -> None:
        """Bucket rules by segment count and first literal segment."""
        self._by_len_first: dict[tuple[int, Optional[str]], list[Rule]] = (
            collections.defaultdict(list)
        )
        for rule in self.rules:
            if not rule.segments:
                continue
            first = rule.segments[0].raw
            literal = None if VAR_RE.search(first) else first
            self._by_len_first[(len(rule.segments), literal)].append(rule)

    def _candidate_rules(self, leaf: Leaf) -> list[Rule]:
        count = len(leaf.segments)
        found = list(self._by_len_first.get((count, None), ()))
        first = leaf.segments[0] if leaf.segments else None
        if first is not None:
            found.extend(self._by_len_first.get((count, first), ()))
        return found

    # ------------------------------------------------------------------
    def translate(self) -> dict[str, Any]:
        self._index_rules()
        leaves = self.doc.leaves
        self.report.total_leaves = len(leaves)

        winners: dict[int, list[tuple[Rule, dict[str, str]]]] = {}
        for position, leaf in enumerate(leaves):
            matches: list[tuple[Rule, dict[str, str]]] = []
            for rule in self._candidate_rules(leaf):
                bindings = rule.match(leaf.segments)
                if bindings is not None:
                    matches.append((rule, bindings))
            if not matches:
                self.report.unmatched_leaves.append(leaf.path)
                continue
            best = max(rule.specificity for rule, _ in matches)
            top = [(rule, binding) for rule, binding in matches if rule.specificity == best]
            if any(rule.is_suppression for rule, _ in top):
                self.report.suppressed_leaves.append(leaf.path)
                continue
            self.report.matched_leaves += 1
            winners[position] = top

        # rule index -> [(leaf, bindings)] in document order
        by_rule: dict[int, list[tuple[Leaf, dict[str, str]]]] = collections.defaultdict(list)
        for position, top in winners.items():
            for rule, bindings in top:
                by_rule[rule.index].append((leaves[position], bindings))

        config: dict[str, dict[str, Any]] = collections.OrderedDict()
        for rule in self.rules:
            hits = by_rule.get(rule.index)
            if not hits:
                continue
            self._apply_rule(rule, hits, config)

        for message in self.values.warnings + self.report.warnings:
            if message not in self._warned:
                self._warned.add(message)
        self.report.warnings = sorted(self._warned)
        return config

    # ------------------------------------------------------------------
    def _apply_rule(
        self,
        rule: Rule,
        hits: list[tuple[Leaf, dict[str, str]]],
        config: dict[str, dict[str, Any]],
    ) -> None:
        """Apply one rule to all OC leaves that matched it.

        ``list_combination`` behaves in two ways:

        * with ``$VALUE_LIST$`` in the target template the leaf value is a
          vlan list and the rule expands once per element;
        * otherwise every matched leaf contributes one element to a JSON list
          on the target field (``DNS|server|ip``, ``SYSLOG_SERVER|...|servers``).

        ``string_combination`` accumulates the rendered values and joins them
        with commas (SONiC comma separated string fields).
        """
        aggregated: dict[tuple[str, str, Optional[str]], list[str]] = collections.OrderedDict()
        joined: dict[tuple[str, str, Optional[str]], list[str]] = collections.OrderedDict()

        for leaf, bindings in hits:
            self.report.rule_fires[rule.index] = self.report.rule_fires.get(rule.index, 0) + 1
            ctx = self._context(leaf, bindings)
            for target_index, template in enumerate(rule.sk_templates):
                selector = (
                    rule.selectors[target_index]
                    if target_index < len(rule.selectors)
                    else rule.selectors[-1]
                )
                candidates = (
                    rule.sv_entries[target_index]
                    if target_index < len(rule.sv_entries)
                    else (rule.sv_entries[-1] if rule.sv_entries else [])
                )
                index = selector_index(selector, ctx, self.values)
                if index is None:
                    continue
                candidate = resolve_candidate(candidates, index)

                directive = selector.value if selector.kind == "directive" else None
                is_list_target = directive == "list_combination"
                is_string_target = directive == "string_combination"

                iterations: list[Optional[str]] = [None]
                if "VALUE_LIST" in VAR_RE.findall(template):
                    raw = ctx.get("_raw_value")
                    if isinstance(raw, list):
                        items = [str(item) for item in raw]
                    else:
                        items = self.values.parse_vlan_list(ctx.get("_value", ""))
                    if items:
                        iterations = list(items)  # type: ignore[list-item]

                for item in iterations:
                    if item is not None:
                        ctx["_value_list_item"] = item
                    value = self._render_candidate(candidate, ctx)
                    if value is OMIT:
                        continue
                    target = self._split_target(template, ctx)
                    if target is None:
                        continue
                    if is_list_target:
                        bucket = aggregated.setdefault(target, [])
                        for text in _flatten(value):
                            if text not in bucket:
                                bucket.append(text)
                        continue
                    if is_string_target:
                        bucket = joined.setdefault(target, [])
                        text = _stringify(value)
                        for part in text.split(","):
                            if part and part not in bucket:
                                bucket.append(part)
                        continue
                    self._store(
                        config, target[0], target[1], target[2], value, rule, leaf.path
                    )

        for (table, key, field_name), values in aggregated.items():
            self._store(config, table, key, field_name, list(values), rule, "<list_combination>")
        for (table, key, field_name), values in joined.items():
            self._store(
                config, table, key, field_name, ",".join(values), rule, "<string_combination>"
            )

    # ------------------------------------------------------------------
    def _context(self, leaf: Leaf, bindings: dict[str, str]) -> dict[str, Any]:
        ctx: dict[str, Any] = dict(bindings)
        ctx["_value"] = leaf.text()
        ctx["_raw_value"] = leaf.value
        ctx["_kind"] = leaf.kind
        ctx["_path"] = leaf.path
        segments = leaf.segments
        if len(segments) >= 3 and segments[0] == "interfaces" and segments[1] == "interface":
            ctx.setdefault("INTERFACE", segments[2])
            ctx.setdefault("NAME", segments[2])
        return ctx

    def _render_candidate(self, candidate: Any, ctx: dict[str, Any]) -> Any:
        # a list candidate is a multi-valued field (``services``, ``ports``, ...)
        if isinstance(candidate, list):
            return [self.values.render(item, ctx) for item in candidate]
        return self.values.render(candidate, ctx)

    def _split_target(
        self, template: str, ctx: dict[str, Any]
    ) -> Optional[tuple[str, str, Optional[str]]]:
        segments = [self.values.render(part, ctx) for part in split_path(template)]
        segments = [segment for segment in segments if segment != "" or True]
        if not segments or segments[0] in ("", "NONE"):
            return None
        table = segments[0]
        if len(segments) == 1:
            return (table, table, None)
        key = segments[1]
        field_name = segments[2] if len(segments) > 2 else None
        return (table, key, field_name)

    def _emit(
        self,
        template: str,
        value: Any,
        ctx: dict[str, Any],
        rule: Rule,
        leaf: Leaf,
        config: dict[str, Any],
    ) -> None:
        target = self._split_target(template, ctx)
        if target is None:
            return
        table, key, field_name = target
        self._store(config, table, key, field_name, value, rule, leaf.path)

    def _store(
        self,
        config: dict[str, Any],
        table: str,
        key: str,
        field_name: Optional[str],
        value: Any,
        rule: Rule,
        oc_path: str,
    ) -> None:
        value = _clean(value)
        if value is OMIT:
            return
        entry = config.setdefault(table, collections.OrderedDict())
        if field_name is None:
            if key in entry and isinstance(entry[key], dict) and value == {}:
                return
            entry[key] = value
        else:
            record = entry.setdefault(key, collections.OrderedDict())
            if not isinstance(record, dict):  # pragma: no cover - defensive
                record = {}
                entry[key] = record
            if field_name in record and record[field_name] == value:
                return
            record[field_name] = value
        self.report.emissions.append(
            Emission(table, key, field_name, value, rule.index, oc_path)
        )


def _stringify(value: Any) -> str:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return "" if value is None else str(value)


def _flatten(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return ["" if value is None else str(value)]


def _clean(value: Any) -> Any:
    """Replace DSL sentinels by plain JSON values."""
    if value is EMPTY_DICT or value == "empty_dict":
        return {}
    if value is OMIT:
        return OMIT
    if isinstance(value, list):
        items = [_clean(item) for item in value]
        return [item for item in items if item is not OMIT]
    return value
