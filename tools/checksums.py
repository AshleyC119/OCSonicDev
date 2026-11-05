"""Write CHECKSUMS.txt: SHA-256 of materials, sources, docs, audits and outputs.

Usage:  python tools/checksums.py [--out CHECKSUMS.txt]
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GROUPS = [
    ("materials", ["data/manifest.json", "data/raw/oc", "references/raw"]),
    ("sources", ["translator", "tests", "tools", "scripts"]),
    ("entry points", ["README.md", "PROMPT.md", "AGENTS.md"]),
    ("documents", ["docs"]),
    ("audits", ["audit"]),
    ("generated", ["outputs"]),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect() -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for group, prefixes in GROUPS:
        for prefix in prefixes:
            path = ROOT / prefix
            if path.is_file():
                files.append((group, path))
            elif path.is_dir():
                for child in sorted(path.rglob("*")):
                    if child.is_file() and "__pycache__" not in child.parts:
                        files.append((group, child))
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(ROOT / "CHECKSUMS.txt"))
    args = parser.parse_args(argv)

    lines = [
        "# SHA-256 checksums for the OC->SONiC translator deliverables.",
        "# Regenerate with: python tools/checksums.py",
        "",
    ]
    for group, path in collect():
        relative = path.relative_to(ROOT).as_posix()
        lines.append(f"{sha256(path)}  {relative}")
    out = Path(args.out)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
