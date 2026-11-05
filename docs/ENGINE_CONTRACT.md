# OC → SONiC translator: shared contract (v1, Lead)

This document is the shared working contract for the whole team. It defines how the
supplier mapping table is read, how the OC document is matched, and the exact JSON
shape the translator emits. Auditors must produce their expected-output files in this
contract's notation so the Lead can diff them mechanically against engine output.

## 1. Inputs (read-only, never modify)

- Rules (manual): `references/raw/yang2sonic_maptable(1).csv`
  - 769 data rows, columns `yang_key,yang_value,sonic_key,sonic_value,spine`.
- OC document: `data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt`
  - one JSON object, UTF-8 (BOM), 15 root keys.

## 2. Rule row model

Each row is one mapping template:

```
yang_key    : '//'-separated pattern over the OC document tree
yang_value  : python-literal selector DSL, e.g. [['unchanged']]
sonic_key   : either one '//'-separated template string, or a python list of them
sonic_value : python-literal value DSL aligned with sonic_key
spine       : the supplier's section label (grouping only)
```

`sonic_key` values in the CSV are python literals: a bare string when there is one
target, a `[...]` list when a row targets several SONiC fields at once. Parse with
`ast.literal_eval`; if that fails, treat the raw text as one template.

### 2.1 yang_key pattern syntax

The OC document is flattened to a list of `(path_segments, value)` pairs, one per
scalar leaf, where every dict key is one segment:

```
acl / acl-sets / acl-set / "SNMP-Filter ACL_CTRL" / acl-entries / acl-entry / "10" / config / sequence-id
```

The pattern is matched segment-by-segment against that list:

- A segment without `$` is a literal; it must equal the document segment exactly.
- `$NAME$` matches any (non-empty) text and binds `NAME` for the rest of the rule.
- Text may surround a placeholder (`Vlan$INTERFACEID$`, `LoopBack$INTERFACEID$`).
- One segment may hold several placeholders separated by literals
  (`$ACL-SET$ $TYPE$` matches `SNMP-Filter ACL_CTRL` ⇒ ACL-SET=SNMP-Filter,
  TYPE=ACL_CTRL).
- `$VALUE$` is bound implicitly to the leaf value; `$VALUE_LIST$` is the value list
  expanded for list-valued leaves (see 3.2). `$INTERFACE$` is bound implicitly to the
  interface name for rules below `interfaces/interface/<name>` (also accept `$NAME$`
  style binding when a segment is a full wildcard).

Placeholder names seen (non-exhaustive): INTERFACE, INTERFACEID, SUBINTERFACE,
ADDRESS, IPVERSION, VLAN, VALUE, VALUE_LIST, GROUP, SERVER, QUEUEID, SET, IP, MASK,
RANGE, PREFIX, COMMUNITY, NEIGHBOR, AREA, NAME, ASIC, PORT.

### 2.2 Rule matching and precedence

For every flattened leaf, all rules whose pattern matches are candidates, except
rules whose `spine` names a table the document does not contain (those simply never
match). Precedence:

1. The candidate set is the one with the largest number of literal (non-placeholder)
   segments. This makes literal rules such as
   `acl//acl-sets//acl-set//SNMP-Filter ACL_CTRL//...` override generic `$ACL-SET$ $TYPE$`
   rules, and lets a rule suppress a broader rule.
2. A rule whose `yang_value` is `[['NONE']]` is a *suppression* rule: it fires, emits
   nothing, and blocks lower-specificity rules for the same leaf (e.g. `eth0`/`BMC`/
   `Vlan$N$`/`GigabitEthernet0` must not become a `PORT` entry).
3. Among the remaining rules at top specificity, apply all in CSV order; a field
   written twice keeps the later value (the engine records a warning).

## 3. Value DSL

### 3.1 selector list (yang_value)

`yang_value` is a list of *selectors*, one per target in `sonic_key` (if a single
target it is one selector). A selector chooses one candidate out of the matching
`sonic_value` list. Observed selector forms:

| yang_value element | meaning |
|---|---|
| `['unchanged']` | pass the OC leaf value through |
| `['true','false']` | enumeration: index of the leaf value in this list selects the `sonic_value` candidate with the same index |
| `['any']` | matches any value (usually paired with `sonic_value` `NONE`) |
| `['NONE']` | suppression rule (see 2.2) |
| `['default']` | constant branch: always candidate 0 |
| `['compute']` | the OC value is transformed, not used literally |
| `['combination']` / `['string_combination']` | output is built from placeholders/other leaves (template substitution) |
| `['list_combination']` | leaf value is a list; see 3.2 |
| `['list_value']` / `['list_2_string']` | exported list value(s); see 3.2 |
| `['empty_dict']` | presence rule: fires when the path exists, not on a specific value |
| `['ockey', <path>]` followed by a branch list | look up the OC value at `<path>` in the same match context, then index the branch list |
| `['lowercase']` | lower-case the value before use |

For `ockey`, the second element is the branch list. Branch strings are compared to
the looked-up value; `ockey_default` is the fallback branch. Examples:

- `[[['ockey',X],['0','1','ockey_default']], ...]` + `sonic_value`
  `[[['primary','secondary','primary']], ...]`: X==0 ⇒ primary, X==1 ⇒ secondary,
  otherwise primary.
- `[[['ockey',X],['ocvalue']], ...]` + sonic candidate `ocvalue` ⇒ substitute the
  looked-up value (e.g. MGMT_INTERFACE gwaddr = mgmt default-route next-hop).

### 3.2 list handling

- `list_combination` with a `$VALUE_LIST$` placeholder in sonic_key ⇒ one emitted
  entry per element of the expanded list (e.g. `trunk-vlans` `2,10-12` ⇒ vlan 2, 10,
  11, 12), with `$VALUE_LIST$` bound to each element.
- `list_combination` without `$VALUE_LIST$` (sonic candidate `value`) ⇒ emit the raw
  string as one value.
- `list_value` ⇒ the value is a list; emit a JSON list when the candidate holds the
  list as-is.

### 3.3 sonic_value candidates

`sonic_value` is a list of candidate lists aligned with the selector branches. A
candidate is a list of items:

- items containing placeholders (`$VAR$`, or a bare variable name from the provider
  vocabulary such as `INTERFACE`, `INTERFACEID`, `ADDRESS`, `SUBINTERFACE`, `GROUP`,
  `NEIGHBOR`, `AREA`, `VALUE`, `VALUE_LIST`) are substituted;
- concatenation is written with `+` (`PortChannel+INTERFACEID`, `ADDRESS+/+value`),
  bare `value`/`ocvalue` mean the leaf value / looked-up ockey value;
- candidate `NONE` ⇒ do not emit that field;
- candidate `empty_dict` ⇒ emit the key with an empty object value `{}`;
- a candidate with several items ⇒ JSON list value, e.g. `services` → `["SNMP"]`;
- otherwise ⇒ JSON string.

Transforms used with `compute`: `original` (leaf value as-is), `original//1000`
(integer division by 1000, e.g. port-speed 200000000 → 200000), `10000-original`
(e.g. ACL sequence-id 10 → 9990), `original//1000` for hold-time ms → seconds.

## 4. sonic_key templates → output shape

Split `sonic_key` on `//`. `[0]` is the SONiC table, `[1]` the key (with `|`-joined
components already written literally, e.g. `Vlan$VALUE_LIST$|PortChannel$INTERFACEID$`),
`[2]` the field. Two segments means "key with empty object value". Placeholders are
substituted from the match bindings.

Emitted JSON (this is the deliverable shape):

```json
{
  "ACL_TABLE": {"SNMP": {"stage": "INGRESS", "services": ["SNMP"], "type": "CTRLPLANE"}},
  "ACL_RULE": {"SNMP|RULE_10": {"PRIORITY": "9990", "PACKET_ACTION": "ACCEPT"}},
  "LOOPBACK_INTERFACE": {"Loopback0|22.141.134.164/32": {}}
}
```

- Tables are JSON objects; keys are `|`-joined strings; field maps are JSON objects.
- All scalar values are JSON strings unless the candidate is a list or `empty_dict`.
- Ordering: tables in order of first emission (rules in CSV order, then document
  order inside a rule); keys in order of first creation; fields in insertion order.
  Ordering is for reproducibility only and must not be used for correctness claims.
- Field name `NONE` is never emitted.

## 5. Auditor deliverable format

Put files under `audit/`. For each assigned rule group:

1. `audit/<group>.expected.txt` — plain text, one line per expected emission, sorted:

   ```
   TABLE|KEY|FIELD = <json-encoded value>
   ```

   `FIELD` may be empty when the emission is a key with `{}` value:
   `LOOPBACK_INTERFACE|Loopback0|22.141.134.164/32 = {}`.
   Each line should be derivable by hand from a rule row; append the rule row index
   and OC path as a comment after `  # ` on the same line when it helps the diff.
2. `audit/<group>.notes.md` — for every rule row in the group: does it fire on this
   OC document (which concrete path), or not (why). Also list ambiguities, places
   where the CSV seems inconsistent, and OC paths with no covering rule.

Never edit files outside your own `audit/` file names, `docs/` notes, and the shared
task description. The Lead owns `translator/` code and `outputs/`.

## 6. Known open questions (Lead)

1. Is `1000` in ACL yang_key a literal entry id or a synthetic "default rule"?
2. Exact precedence when several same-specificity rules hit one leaf.
3. Whether `$INTERFACE$` should bind for `interfaces/interface/<name>` even when the
   rule uses literal names (`eth0`, `BMC`).
4. Whether `VLAN` `description`/`vlanid` come from `interfaces/interface/VlanN` (the
   doc's `network-instances/.../vlans` subtree has its own `config/name`).
