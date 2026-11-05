"""Flatten the OC document into matchable leaves.

The supplier table addresses the OC tree as ``//``-separated *segments*, one
segment per JSON object key.  List entries are keyed objects in this document
(``{"acl-entry": {"10": {...}}}``), so flattening is a plain recursive walk.

Every leaf records its segment path, its value and a *kind*:
``scalar``, ``list`` (JSON array of scalars) or ``empty`` (an ``{}`` object).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class Leaf:
    segments: tuple[str, ...]
    value: Any
    kind: str  # scalar | list | empty

    @property
    def path(self) -> str:
        return "//".join(self.segments)

    def text(self) -> str:
        """The value as the string the rules compare against."""
        if isinstance(self.value, bool):
            return "true" if self.value else "false"
        if isinstance(self.value, (int, float)):
            return str(self.value)
        if isinstance(self.value, list):
            return ",".join(str(item) for item in self.value)
        if isinstance(self.value, dict):
            return ""
        return "" if self.value is None else str(self.value)


class OcDocument:
    """Flattened view of one OC document with path lookup helpers."""

    def __init__(self, data: dict):
        self.data = data
        self.leaves: list[Leaf] = []
        self._index: dict[tuple[str, ...], Leaf] = {}
        self._flatten(data, [])
        for leaf in self.leaves:
            self._index.setdefault(leaf.segments, leaf)

    # ------------------------------------------------------------------
    def _flatten(self, node: Any, path: list[str]) -> None:
        if isinstance(node, dict):
            if not node:
                leaf = Leaf(tuple(path), {}, "empty")
                self.leaves.append(leaf)
                self._index.setdefault(leaf.segments, leaf)
                return
            for key, value in node.items():
                self._flatten(value, path + [str(key)])
            return
        if isinstance(node, list):
            if all(not isinstance(item, (dict, list)) for item in node):
                leaf = Leaf(tuple(path), list(node), "list")
                self.leaves.append(leaf)
                self._index.setdefault(leaf.segments, leaf)
                return
            for position, item in enumerate(node):
                self._flatten(item, path + [str(position)])
            return
        leaf = Leaf(tuple(path), node, "scalar")
        self.leaves.append(leaf)
        self._index.setdefault(leaf.segments, leaf)

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: str) -> "OcDocument":
        with open(path, "rb") as handle:
            raw = handle.read()
        return cls(json.loads(raw.decode("utf-8-sig")))

    def get(self, segments: tuple[str, ...]) -> Optional[Leaf]:
        return self._index.get(segments)

    def lookup_prefix(self, segments: tuple[str, ...]) -> Optional[Leaf]:
        """First leaf whose path starts with ``segments`` (container lookup)."""
        for leaf in self.leaves:
            if leaf.segments[: len(segments)] == segments:
                return leaf
        return None
