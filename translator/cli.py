"""Command line interface: translate one OC document with the mapping table."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .engine import Translator
from .ocdoc import OcDocument
from .rules import load_rules

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = REPO_ROOT / "references" / "raw" / "yang2sonic_maptable(1).csv"
DEFAULT_OC = REPO_ROOT / "data" / "raw" / "oc" / "CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt"
DEFAULT_OUT = REPO_ROOT / "outputs" / "CQ-JLDC-2203-D05-TCS84R-LA200G-019.sonic.json"
DEFAULT_REPORT = REPO_ROOT / "outputs" / "translate_report.json"
DEFAULT_DETAILS = REPO_ROOT / "outputs" / "translate_details.txt"


def translate(rules_path: Path, oc_path: Path) -> tuple[dict, dict]:
    rules = load_rules(str(rules_path))
    document = OcDocument.load(str(oc_path))
    translator = Translator(rules, document)
    config = translator.translate()
    detail_lines = [
        f"{emission.render_line()}  # rule {emission.rule_index} {emission.oc_path}"
        for emission in translator.report.emissions
    ]
    report = {
        "rules_file": str(rules_path),
        "oc_file": str(oc_path),
        "summary": translator.report.summary(),
        "warnings": translator.report.warnings,
        "unmatched_leaves": translator.report.unmatched_leaves,
        "suppressed_leaves": translator.report.suppressed_leaves,
        "rules_fired": {str(k): v for k, v in sorted(translator.report.rule_fires.items())},
        "details": detail_lines,
    }
    return config, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Translate an OC configuration document into SONiC config JSON "
        "using the supplier yang2sonic mapping table."
    )
    parser.add_argument("--rules", default=str(DEFAULT_RULES), help="mapping table CSV")
    parser.add_argument("--oc", default=str(DEFAULT_OC), help="OC document (JSON) to translate")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="output SONiC config JSON")
    parser.add_argument(
        "--report", default=str(DEFAULT_REPORT), help="diagnostics report JSON"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="do not print the summary"
    )
    args = parser.parse_args(argv)

    config, report = translate(Path(args.rules), Path(args.oc))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    details_path = report_path.with_name("translate_details.txt")
    details_path.write_text("\n".join(report.pop("details")) + "\n", encoding="utf-8")
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    if not args.quiet:
        summary = report["summary"]
        print(f"rules:      {args.rules}")
        print(f"oc:         {args.oc}")
        print(f"leaves:     {summary['total_leaves'] if 'total_leaves' in summary else summary['leaves']}")
        print(f"matched:    {summary['matched_leaves']}")
        print(f"unmatched:  {summary['unmatched_leaves']}")
        print(f"suppressed: {summary['suppressed_leaves']}")
        print(f"emissions:  {summary['emissions']}")
        print(f"tables:     {len(summary['tables'])}")
        for table, count in summary["tables"].items():
            print(f"  {table:28s} {count}")
        print(f"written:    {out_path}")
        print(f"report:     {report_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
