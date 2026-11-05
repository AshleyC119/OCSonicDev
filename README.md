# OCSonicDev — OC → SONiC configuration JSON translator

A rule-driven translator that converts an OC-style configuration document into a
SONiC-style configuration JSON document.  All behaviour comes from the supplier
mapping table `references/raw/yang2sonic_maptable(1).csv`; no device name or
input hash is special-cased.

## Quick start

```powershell
# translate the supplied OC document (writes outputs/…sonic.json)
python -m translator

# explicit paths
python -m translator --rules "references/raw/yang2sonic_maptable(1).csv" `
                     --oc "data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt" `
                     --out "outputs/CQ-JLDC-2203-D05-TCS84R-LA200G-019.sonic.json" `
                     --report "outputs/translate_report.json"
```

The command writes three artefacts:

| file | content |
| --- | --- |
| `outputs/<oc>.sonic.json` | the translated SONiC configuration |
| `outputs/translate_report.json` | totals, unmatched OC leaves, suppressed leaves, per-rule fire counts, warnings |
| `outputs/translate_details.txt` | one line per emission (`TABLE\|KEY\|FIELD = value`) with the rule row and OC leaf it came from |

Verification and diagnostics:

```powershell
python scripts/verify_materials.py                 # raw materials unchanged
python -m unittest discover -s tests -v            # unit tests
python tools/diagnose.py                           # regenerate docs/coverage.md
python tools/audit_diff.py audit/*.expected.txt    # diff against hand-derived audits
```

## How it works

1. `translator/rules.py` parses every CSV row into a `Rule`: a `yang_key` segment
   pattern (`$VAR$` wildcards), a selector list from `yang_value`, one or more
   `sonic_key` templates and the aligned `sonic_value` candidate lists.
2. `translator/ocdoc.py` flattens the OC document into `(segments, value)` leaves;
   keys become path segments, so `acl/acl-set/"SNMP-Filter ACL_CTRL"/...` is
   matched as one segment.
3. `translator/engine.py` matches every leaf against the rules, keeps the most
   specific matches (literal length beats wildcards; `NONE` rows suppress broader
   rows), then evaluates each rule in CSV order and writes
   `TABLE → KEY → FIELD` into the output document.
4. `translator/values.py` implements the value DSL: `unchanged`, enumerations,
   `default`/`any`/`empty_dict`/`list_value`/`list_2_string`/`lowercase`,
   `compute` transforms (`10000-original`, `original//1000`, `log2(original)`),
   `ockey` lookups with branch lists and `ockey_default`, `combination`
   templates (`+` concatenation, `[TABLE|KEY]` references, `{|ockey=...}` key
   suffixes), `list_combination` (per-element expansion for `$VALUE_LIST$` and
   JSON-list accumulation otherwise) and `string_combination` (comma-joined
   accumulation).

`docs/ENGINE_CONTRACT.md` is the written contract for the rule language,
`docs/dsl-semantics.md` the detailed directive reference, `docs/coverage.md` the
measured coverage of the supplied document, and `docs/TRANSLATOR_NOTES.md` the
supported range, assumptions and unsupported cases.

## Repository layout

```
translator/            implementation (importable package)
  rules.py             mapping-table loader / pattern compiler
  ocdoc.py             OC document flattening and path lookup
  values.py            value-DSL evaluation
  engine.py            matching, emission, report
  cli.py, __main__.py  command line entry point
tests/                 unit tests
tools/                 diagnose.py, audit_diff.py
docs/                  contract, DSL semantics, coverage, notes
audit/                 independent hand-derived expected outputs per rule group
data/, references/     supplied raw materials (read-only)
outputs/               generated artefacts
```

## Fixing the materials

`python scripts/verify_materials.py` checks both supplied files byte-for-byte
against `data/manifest.json`; the translator only reads them.
