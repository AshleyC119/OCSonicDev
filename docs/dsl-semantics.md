# Supplier mapping-table DSL: decoded semantics (v1, dsl-analyst)

Status: reference implementation of the rules in
`references/raw/yang2sonic_maptable(1).csv` (769 data rows, 856 `sonic_key`
templates). Written by exhaustive analysis of all 769 rows plus the OC document
`data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt`. Every claim below cites
rule row indexes (0-based data-row order: row 0 is
`acl//acl-sets//acl-set//SNMP-Filter ACL_CTRL//...//sequence-id`) and concrete OC
paths. Confidence is stated where the table is ambiguous.

This file supersedes section 3 of `docs/ENGINE_CONTRACT.md`; contract corrections
are collected in §9.

---

## 1. CSV row model

```
yang_key    : '//'-separated path pattern over the OC tree
yang_value  : python literal, one selector per sonic target
sonic_key   : python literal: one '//'-template string, or a list of them
sonic_value : python literal, one candidate list per sonic target
spine       : supplier section label (used only for grouping/audit)
```

Facts from the full table:

* 723 rows have a single target (`sonic_key` is a string), 46 rows have 2–8
  targets (`sonic_key` is a list; the max is 8, rows 698/699).
* 3 pairs of rows are byte-identical duplicates (206/207, 259/264, 278/283)
  and therefore harmless under "apply all in CSV order" (§3.3).
* `sonic_value` has 78 distinct literal forms; `yang_value` has 54.

## 2. Per-target alignment (normalisation of the nested literals)

For a row with `n` targets, `yang_value` and `sonic_value` both carry one entry
per target. The literals are written with one level of nesting noise that must be
normalised; the rule that reproduces **all 769 rows** is:

```
yspec_j = yang_value[j]        (j = 0 when n == 1)
sspec_j = sonic_value[j]       (j = 0 when n == 1)

# selector: repeatedly unwrap a one-element list containing a list
while len(yspec) == 1 and isinstance(yspec[0], list):
    yspec = yspec[0]

# candidate set: unwrap exactly one wrapper level
if len(sspec) == 1 and isinstance(sspec[0], list):
    cands = sspec[0]
else:
    cands = sspec
```

Evidence for the "one wrapper level" on `sonic_value`: row 0 (2 targets)
`SV=[['2048']]` → ETHER_TYPE `"2048"` (scalar); row 58 `SV=[[['SNMP']]]` →
`services = ["SNMP"]` (one *more* level = JSON list, §5.4); row 612
`SV=[['[DSCP_TO_TC_MAP|global-dscp2tc-profile]', '[DSCP_TO_TC_MAP|default]']]`
→ 2 alternatives for the single branch = fallback chain (§5.5).

Inconsistencies in the literal nesting that a parser MUST tolerate (all verified):

* Single-target ockey rows are written in two ways: with the selector wrapped
  once (`[[['ockey',p],['0','1','ockey_default']]]`, rows 88, 102) and unwrapped
  (`[['ockey',p],['0','1','ockey_default']]`, rows 71, 77, 116, 120, 154, 155).
  Both mean the same thing.
* Simple selectors in multi-target rows are written `[['default']]` (rows 0, 58,
  88, 98, 187, …), i.e. one extra list level compared with the single-target
  form `['default']` (rows 2, 60, 64). This is noise; unwrapping fixes it.
* Some candidate lists are wrapped twice (`[[['SNMP']]]`, row 58) because the
  field value is itself a JSON list.

## 3. `yang_key` pattern matching

### 3.1 Flattening the OC document

Flatten `dict`s key by key. A **JSON array whose elements are scalars is one
leaf with a list value** (the document uses dict-of-dict encoding for real
YANG lists; every array in this document is a leaf-list: `community-member`,
`communities`, `import-policy`/`export-policy`, `helper-address`). Do *not*
index leaf-lists into separate leaves — rows 400/649 depend on seeing the whole
list at one path.

```
acl / acl-sets / acl-set / "2000_IVLAN ACL_IPV4" / acl-entries / acl-entry / 10 / config / sequence-id
```

### 3.2 Segment syntax

A pattern segment is a sequence of literal text and `$NAME$` placeholders.
`$NAME$` matches any non-empty text (shortest match between the surrounding
literals); a segment may contain several placeholders. Examples that occur:

| pattern segment | binds |
|---|---|
| `$ACL-SET$ $TYPE$` on `SSH-Filter ACL_CTRL` | ACL-SET=`SSH-Filter`, TYPE=`ACL_CTRL` |
| `IPV$VERSION1$_UNICAST` on `IPV4_UNICAST` | VERSION1=`4` |
| `$IPADDR$ $PORT$` on `1.2.3.4 8080` | IPADDR=`1.2.3.4`, PORT=`8080` |
| `LoopBack$INTERFACEID$` on `Loopback0` | **no match** (literal "LoopBack" ≠ "Loopback"; rows 82/83 never fire on this doc) |
| `$PBR-NAME$ $NEXTHOP$ $INTF-NAME$` | hyphen allowed in placeholder names |

Special bindings (implicit, not from a segment): `$VALUE$` = the matched leaf
value (scalars only), `$VALUE_LIST$` = current element of the expanded leaf list
(§7.2). Recommended for robustness (not exercised by this document, because the
only rules that need it are suppression rules): `$INTERFACE$` = the 3rd segment
for paths `interfaces/interface/<name>/...`; `$NETWORK$` = 3rd segment for
`network-instances/network-instance/<name>/...`.

### 3.3 Applicability & precedence

A leaf is processed as follows:

1. Find every rule whose pattern matches the leaf (same number of segments;
   placeholders bind consistently).
2. **Specificity** = `(#segments containing at least one non-whitespace literal
   character, #non-whitespace literal characters)`, compared lexicographically.
   Keep only the rules with the maximum specificity.
3. If any kept rule's first selector is the `NONE` op (§4.2), the leaf is
   **suppressed**: nothing is emitted for it by any lower-specificity rule.
4. Otherwise apply all kept rules in CSV order.

Why not contract §2.2's "largest number of literal (non-placeholder) segments":
with that metric `Bridge-Aggregation$INTERFACEID$` does not count as literal, so
`interfaces//interface//$INTERFACE$//config//description` (row 134) ties with
`...//Bridge-Aggregation$INTERFACEID$//config//description` (row 90) and would
emit bogus `PORT|Bridge-Aggregation13|description` entries. Counting
*segments that contain literal text*, then literal characters, reproduces the
obviously intended winners for all 4335 leaves and leaves only the 3 duplicate
pairs tied. Concrete winners:

| leaf | winner | loser(s) |
|---|---|---|
| `interfaces/interface/Bridge-Aggregation13/config/enabled=true` | 91 (PORTCHANNEL admin_status) | 135 (`PORT|Bridge-Aggregation13`) |
| `interfaces/interface/eth0/config/enabled=true` | 74 (`NONE`) | 135 |
| `interfaces/interface/Vlan2/config/enabled=true` | 118 (`NONE`) | 135 |
| `interfaces/interface/Loopback0/config/enabled=true` | 85 | 135 |
| `.../BMC/subinterfaces/subinterface/0/ipv4/addresses/address/28.239.79.69/config/prefix-length` | 70 (BMC ipmask) | 154, 155 |
| `.../eth0/.../22.156.39.15/config/prefix-length` | 71 (MGMT gwaddr) | 154, 155 |
| `.../Loopback0/.../22.141.134.164/config/prefix-length` | 88 (LOOPBACK type) | 154 (9 lit segs but 80 lit chars vs 88's 91), 155 |
| `interfaces/interface/Eth200GE17/config/description` | 134 | — |

Consequence: rows 154/155 (`INTERFACE`, `VLAN_SUB_INTERFACE` type) fire on
**nothing** in this document, so no `INTERFACE`/`VLAN_SUB_INTERFACE` table is
produced (the document has addresses only on `eth0`, `BMC`, `Loopback0`,
`Vlan2`, all of which have a more specific rule).

## 4. Value DSL — `yang_value` selectors

### 4.1 Selector forms

A selector is either

* `["op"]` — one of the always-match ops (§4.3);
* `["v1","v2",…]` — an enumeration: the rule fires only if the leaf value equals
  one of the labels, and the label index selects the candidate;
* `[["ockey", path], [label, …]]` — ockey lookup: resolve `path` (placeholders
  substituted from the current bindings/files), then choose a branch (§4.4).

The candidate list in `sonic_value` is aligned 1:1 with these labels
(`b` labels ⇒ `b` alternatives), except that
* one alternative with `b == 1` is the single result;
* `b == 1` and >1 alternatives = fallback chain of references (§5.5).

### 4.2 The ops

| op | match condition | result side |
|---|---|---|
| `unchanged` | always | `"unchanged"` = the leaf value |
| `any` | always | usually `NONE` (emit nothing) |
| `NONE` | always | fires but emits nothing and **suppresses** lower-specificity rules for the same leaf |
| `default` | always | constant candidate (branch 0) |
| `empty_dict` | always (leaf must exist) | `"empty_dict"` = emit the key with `{}` (presence) |
| `compute` | always | candidate is a transform of the leaf value (`original`, `original//1000`, `10000-original`, `log2(original)`) |
| `combination` | always | candidate is a template built from bindings/leaf value (`ADDRESS+/+value`, `GROUP`, `ACL-SET`, …) |
| `string_combination` | always | accumulate the evaluated candidate across all matches, comma-joined |
| `list_combination` | always | accumulate evaluated candidates into one JSON list (per match), or expand `$VALUE_LIST$` |
| `list_value` | always | leaf value is a JSON list; emit it as a JSON list |
| `list_2_string` | always | leaf value is a JSON list; join into a string |
| `lowercase` | always | lower-case the leaf value |
| `ockey` | see §4.4 | branch-selected candidate |

`["true","false"]` etc. are enumerations, not ops. The document stores all
4335 scalar leaves as strings, so `true`/`false` compare as `"true"`/`"false"`
(serialisers may still see JSON booleans in other inputs; normalise to
`"true"`/`"false"`).

### 4.3 Worked selector examples

* `unchanged` — row 119 `interfaces//interface//Vlan$INTERFACEID$//config//description`
  on `interfaces/interface/Vlan2/config/description = "PM&VM-Access"` ⇒
  `VLAN|Vlan2|description = "PM&VM-Access"`.
* enumeration — row 135 `interfaces//interface//$INTERFACE$//config//enabled`
  with `["true","false"]`/`["up","down"]` on
  `interfaces/interface/Eth200GE1/config/enabled = "down"` ⇒
  index 1 ⇒ `PORT|Eth200GE1|admin_status = "down"`.
  Enum comparison is **exact/case-sensitive** (see open question Q1 for row 101).
* `compute` — row 144 `...//hold-time//config//up = "2000"` and `original//1000`
  ⇒ `PORT|Eth400GE27|up_delay_interval = "2"`; row 138
  `.../ethernet/config/port-speed = "200000000"` ⇒ `PORT|Eth400GE27|speed =
  "200000"`; row 3 `10000-original` ⇒ ACL `PRIORITY = 9990` for entry 10.
* `combination` — row 70
  `interfaces//interface//BMC//subinterfaces//subinterface//$SUBINTERFACE$//ipv4//addresses//address//$ADDRESS$//config//prefix-length`
  with `ADDRESS+/+value` on `.../28.239.79.69/config/prefix-length = "26"` ⇒
  `BMC|INTERFACE|ipmask = "28.239.79.69/26"`; the literal key segment
  `INTERFACE` in rows 68/70 is **not** `$INTERFACE$` and stays literal.
  Row 121 `interfaces/interface/Vlan2/name = "Vlan2"` with `INTERFACEID` ⇒
  `VLAN|Vlan2|vlanid = "2"`.
* `any` + `NONE` — rows 23–54 pin every SNMP/SSH ACL entry field (`DST_IP`,
  `SRC_IP`, `L4_*_PORT`, `IP_PROTOCOL` for protocol `ip`) to `NONE`: the rule
  fires and emits nothing. They cannot suppress anything else on those leaves
  (they are the most specific rules for them).
* `NONE` suppression — `interfaces/interface/eth0/config/enabled = "true"`:
  rows 74 (literal `eth0`) and 135 (generic) both match; 74 wins and emits
  nothing, therefore `PORT|eth0|admin_status` must not appear. Same for BMC
  (row 69), Vlan2 (118), GigabitEthernet0 (78/79, no such interface here) and
  eth0 description (row 76).
* `empty_dict` — row 160
  `lacp//interfaces//interface//Bridge-Aggregation$INTERFACEID$//members//member//$MEMBER$//interface`
  on 16 lacp members ⇒ `PORTCHANNEL_MEMBER|PortChannelN|Eth200GEN` with `{}`;
  also rows 256 (NTP_SERVER), 438 (VRF), 169/170 (L2_MC_GROUP_MEMBER).
* `lowercase` — row 674 on `.../sliceall/input/config/limit-mode "dynamic"`
  ⇒ `BUFFER_POOL|ingress_lossy_pool|mode = "dynamic"`.

### 4.4 `ockey`

```
[["ockey", path], [label, …]]
```

Resolve `path` in the document after substituting current bindings (the path may
reuse `$INTERFACEID$`, `$ADDRESS$`, `$GROUP$`, …). Then:

| label | meaning |
|---|---|
| a literal (`"0"`, `"1"`, `"empty_dict"`?, …) | matches when the looked-up scalar equals the label |
| `ocvalue` | matches whenever the path resolves; the branch result `"ocvalue"` = the looked-up value |
| `ockey_default` | fallback branch when the path is missing or no literal matches |
| `default` | unconditional branch (row 649 target 3) |
| `combination_ocvalue` | unconditional branch; the looked-up value is made available to the reference template (rows 614, 668) |
| `empty_dict` | matches when the path resolves to an empty dict (row 88 target 2, unexercised here) |

Missing path + no fallback label ⇒ rule does not fire. Worked examples:

* row 71 `interfaces//interface//eth0//subinterfaces//subinterface//$SUBINTERFACE$//ipv4//addresses//address//$ADDRESS$//config//prefix-length`
  with branch list `["ocvalue"]` and ockey path
  `network-instances//network-instance//mgt_vrf//...//0.0.0.0/0//next-hops//next-hop//1//config//next-hop`,
  which resolves to `22.156.39.1`. ⇒ `MGMT_INTERFACE|eth0|22.156.39.15/26|gwaddr
  = "22.156.39.1"`.
* row 88 on `Loopback0/22.141.134.164/config/prefix-length`: ockey path
  `.../config//index` is **missing**, branch list `["0","1","ockey_default"]`,
  candidates `["primary","secondary","primary"]` ⇒ `ockey_default` ⇒
  `"primary"`. Row 120 on `Vlan2/routed-vlan/ipv4/addresses/address/*/config/prefix-length`
  → indices `0,1,1` ⇒ `primary, secondary, secondary`.
* rows 187/188: ockey path `system//monitor-link//groups//group//$GROUP$//downlink//config//up-delay`
  resolves `"120"`, branch `["ocvalue"]` ⇒ `PORTCHANNEL|PortChannelN|updelaytime
  = "120"` and `PORT|Eth200GE17|updelaytime = "120"`.
* row 649: ockey on `community-set//config//community-set-name` (`"10"`) and
  `...//config//forwarding-action` (`"permit"`) puts those into the key
  `BGP_COMMS|10|permit|1:1|list_number/opt_type`, and the `default` branch emits
  `mode = "standard"`.
* row 614: `combination_ocvalue` supplies the scheduler-policy name to the
  reference `[SCHEDULER|scheduler.+ocvalue+.+value+]`.

`ocvalue_range_ge` / `ocvalue_range_le` (rows 666/667) are result expressions for
an `ockey` whose looked-up value is `masklength-range` (`"32"`, `"exact"`,
`"24..32"`): intended to split the range into SONiC `ge`/`le`. They are
**unexercised** by this document (rows 666/667 never match, see §8) and their
exact split rule is unknown — flag, do not invent.

## 5. Value DSL — `sonic_value` results

### 5.1 Result atoms

A result is a string or a list (list = JSON array value; or a fallback chain).

| atom | emission |
|---|---|
| `"NONE"` | do not emit the field |
| `"empty_dict"` | emit the key/field with `{}` |
| `"unchanged"`, `"value"`, `"original"` | leaf value |
| `"ocvalue"` | looked-up ockey value (skip field if none) |
| `"list_value"` | leaf list as JSON list (scalars are wrapped: `["x"]`) |
| `"list_2_string"` | leaf list joined with `,` (separator unverified; doc has only single-element lists here, rows 656 `comm_range="1:1"`) |
| `"lowercase"` | lower-cased leaf value |
| `"original//1000"` | integer division by 1000 |
| `"10000-original"` | `10000 - int(leaf)` |
| `"log2(original)"` | `int(log2(int(leaf)))` |
| `"[TABLE|template]"` | reference: evaluate `template`; emit it as the field value and treat `(TABLE, value)` as a referenced object (§5.5) |
| anything else | template (§5.2) |

### 5.2 Templates and `+`

`$NAME$` placeholders are substituted from bindings; `$VALUE$`/`$VALUE_LIST$`
from the leaf/current list element. In addition the result strings are written
without `$` for well-known names, e.g. `ADDRESS+/+value`,
`PortChannel+INTERFACEID`, `IPADDR+:+PORT`, `scheduler.+ocvalue+.+value+`,
`ingress_profile_+INTERFACE+_+QUEUEID+`. Decoding: split on `+`; a part that is a
bound name (or `value`/`ocvalue`/`VALUE_LIST`) is substituted, other parts are
literal; concatenate. A string containing `+` with **no** bound name is literal
(`"tacacs+,local"`, row 198). Rule: apply the split only when at least one part
is a known name, otherwise keep the string verbatim. Worked examples:
`ADDRESS+/+value` ⇒ `28.239.79.69/26` (row 70);
`PortChannel+INTERFACEID` ⇒ `PortChannel13` (row 99);
`[BUFFER_PROFILE|ingress_profile_+INTERFACE+_+QUEUEID+]` ⇒
`ingress_profile_Eth400GE27_5` (row 681).

### 5.3 Constant branches

Rows 137 (`["true"]` → `["1"]`) and 143 (`none/fec/rs-fec` → `none/fc/rs`) show
enumerations with different label/result cardinality being aligned by index;
row 612 shows a *single*-label selector `["true"]` with 2 reference alternatives,
which is a fallback chain, not a JSON list.

### 5.4 JSON-list values

A field is emitted as a JSON array when the selected result atom is itself a
list (rows 58/59 `services=["SNMP"]`, `ports=[""]`; row 698 target 8
`ports=["PORTS"]`), or when the op is `list_combination` (row 99
`VLAN|Vlan2|members=["PortChannel13",…]`, row 254 `SYSLOG_SERVER|syslog_server|servers`,
row 348 `DNS|server|ip`), or `list_value` (row 400
`BGP_REDISTRIBUTES_IPV4|kernel|routemap=["From-Direct"]`).

### 5.5 References and fallback chains

`[TABLE|key-template]` appears in rows 612, 613, 614, 617, 677, 680, 681, 745,
749, 768 and always denotes "value = the *key* (name) of an object of TABLE"
(e.g. `QUEUE|Eth400GE27|5|scheduler = "scheduler.DWRR.50"`,
`BUFFER_QUEUE|Eth400GE27|5|profile = "egress_profile_Eth400GE27_5"`). When a
branch has several alternatives (row 612: prefer `global-dscp2tc-profile`, else
`default`) they are tried in order and the first existing target object wins.
Existence must be decided on the **final** object set (a second pass), because
e.g. row 612 is applied before the buffer/map rows that create the objects.
References to objects this document never creates (`[EBST_PROFILE|…]`, rows
617/768 etc.) should be dropped (or emitted verbatim: unknown, flag).

## 6. `sonic_key` templates

Split on `//` into `table // key // field` (2 segments = "key only, empty
object"). Table, key and field are all templates; `$VALUE$` is the leaf value
(e.g. row 258 `SNMP_AGENT_ADDRESS_CONFIG|$SERVER$|$VALUE$|mgmt`). Literal
components inside the key are common: `SNMP|DEFAULT_RULE`, `$COMMUNITY$|permit|…`,
`0|- -|router`.

Special syntax: `$VALUE${|ockey=PATH}` (row 493) means: append `|` and the value
found at PATH (the brace syntax only occurs in that row). Splitting must protect
`{...}` because the embedded path contains `//`.

## 7. Expansion and accumulation

### 7.1 Leaf lists

An OC leaf whose value is a JSON array (leaf-list) is one leaf with a list value;
`list_value`/`list_2_string` consume it whole, `$VALUE_LIST$` iterates its
elements.

### 7.2 `$VALUE_LIST$` expansion

If any target's key template contains `$VALUE_LIST$`, the rule is applied once
per element of the leaf list (`community-member = ["1:1","1:2","1:4","1:65019"]`
⇒ four `BGP_COMMS|10|permit|<member>` keys, row 649; `native-vlan = "2"` ⇒ one
element `"2"`, rows 98–100). A scalar is treated as a one-element list. For a
comma/range string (`"2,10-12"`, `"10..20"`) expand to vlan ids (unexercised by
this document — the OC fields only hold single vlans here).

### 7.3 Merge modes into the output JSON

| mode | used by | behaviour |
|---|---|---|
| scalar set | all ops except the two below | last write wins; row order + document order decide |
| list append | `list_combination` | append evaluated candidate (extend if candidate is a list) to the JSON array of the field; order = document order |
| string append | `string_combination` | append `,` + value to a string field |

Evidence for list append: row 99 `VLAN|Vlan2|members` grows to 16 PortChannels
(one per Bridge-Aggregation native-vlan leaf), row 254 `servers`, row 348
`DNS|server|ip`. Evidence for string append: rows 698/699
`ACL_RULE|IFA_INGRESS|RULE_1001|IN_PORTS` becomes
`"Eth400GE27,Eth400GE28,…"` (32 interfaces) and rows 615/616 `pri_enable`/
`pfc_enable = "5"`.

`combination` is **not** an accumulator: each leaf writes its own key/field
(row 70, 121, 494, 649 target 0).

## 8. Row-status summary for the audited groups

`audit/dsl.expected.txt` is derived from rows 68–157 (`interfaces//interface`),
187–195 (`system//monitor-link`) and 649/666/667/668 (`routing-policy//defined-sets`).

* Fire in this document: 70, 71, 85, 88, 90–95, 99, 103, 119–123, 126,
  134–139, 143–147, 153 (interfaces); 188, 189, 193, 195 (monitor-link);
  649 (routing-policy).
* Suppression-only (`NONE`): 69, 74, 76, 78, 79, 118.
* Never match this document: 68 (`ip` selector, Q2), 72 (no interface vrf),
  73 (no `enabled-dci`),
  75 (no alias), 77 (no `GigabitEthernet0`), 80/81 (`Netsense` tunnel absent),
  82/83 (`LoopBack` vs `Loopback` casing), 84 (`LoopBack` casing), 86/87 (no
  interface vrf), 89 (no IPv6 loopbacks), 96/97 (no `lag-type`/`min-links`),
  98/100 (no trunk/access vlan), 101 (`ACCESS/TRUNK` casing, Q1), 102/116
  (no port-channel addresses), 104–117 (`port-channel*` lowercase; doc uses
  `Bridge-Aggregation*`), 124/125/127–133 (missing leaves), 140–142 (no
  storm-control), 148/149 (no alias/index), 150–152 (no ethernet trunk/native/
  access vlan), 154/155 (outranked by 70/71/88, §3.3), 156/157 (no subinterface
  vrf), 187/190/191/194 (no BA uplinks / no `port-channel`), 192 (no
  `port-channel`).
* 666/667: `.../prefix//$IP$/$MASK$ $RANGE$//config//sequence-id` does not exist
  in this document (`prefix` entries only carry `ip-prefix`,
  `masklength-range`, `ip-prefix,masklength-range`, `config`), and
  `$SET$IPv6` does not match `Host-Route`/`LOOPBACK0`. 668: no
  `bgp-access-lists` subtree. So **no `BGP_IPPREFIXLIST`/`BGP_ACCESSLIST`
  table is produced**, even though `routing-policy/defined-sets/prefix-sets`
  exists; only row 649 fires (36 `BGP_COMMS` fields).

## 9. Contract corrections (docs/ENGINE_CONTRACT.md)

1. **§2.2 specificity is wrong.** Counting fully-literal segments lets generic
   `$INTERFACE$` rules win ties against `Bridge-Aggregation$INTERFACEID$` /
   `Loopback$INTERFACEID$` / `Vlan$INTERFACEID$` rules, which would create
   `PORT` entries for port-channels, VLANs and loopbacks. Use
   `(#segments with non-whitespace literal text, #non-whitespace literal chars)`.
2. **§3.2 list_combination "without $VALUE_LIST$ ⇒ emit raw string as one value"
   is wrong.** `list_combination` means "this field is a JSON list, accumulated
   over matches"; `$VALUE_LIST$` in the key additionally expands one iteration
   per list element.
3. **§3.3 "candidate with several items ⇒ JSON list" is only half true.** A
   multi-item candidate for a 1-branch selector is a *fallback chain of
   references* (row 612). A JSON list value is a candidate that is itself a list
   nested one level deeper (rows 58/698), or an op-level list op.
4. **§2.1 flattening must keep leaf-lists whole** (community-member etc.), not
   index them; otherwise rows 400/649 never match.
5. **§6 Q1 answered:** `1000` in the ACL yang_keys is a literal acl-entry id;
   the document really contains entry `1000` (e.g.
   `acl/acl-sets/acl-set/2000_IVLAN ACL_IPV4/acl-entries/acl-entry/1000`), and
   the literal SNMP/SSH rules rename it to `DEFAULT_RULE`. It is not a
   synthetic placeholder. Rows 0/1 address the list key's `sequence-id`, rows
   2/4 the `config//sequence-id`; both leaves exist.
6. **§6 Q3 answered:** implicit `$INTERFACE$` binding is not needed by any rule
   that fires here (rows 69/74/76/78/79/118 are `NONE`; row 68/70's key
   component `INTERFACE` is a literal). Support it anyway for robustness.
7. **§6 Q2:** same-specificity conflicts: only 3 leaves where two rules tie, and
   they are byte-identical duplicate rows (206/207, 259/264, 278/283).
8. **§6 Q4:** `VLAN|Vlan2|vlanid/description/…` come from
   `interfaces/interface/Vlan2` (rows 119/121), not from
   `network-instances/.../vlans`; the latter subtree is not targeted by any
   `interfaces` rule.

## 10. Open questions / unresolved (do not guess silently)

* **Q1 (high impact): enum comparison case.** Row 101/115 selectors are
  `['ACCESS','TRUNK','route']` but the document stores `"trunk"` (Bridge-
  Aggregations, 16 leaves) and `"route"` (Ethernet). Exact comparison ⇒ no
  `PORTCHANNEL|PortChannelN|switchmode`; case-insensitive ⇒ 16 additional
  `switchmode="trunk"` lines. Only this rule family is affected (verified over
  the whole document). `dsl.expected.txt` uses exact comparison.
* **Q2: row 68** `interfaces//interface//BMC//bmc//config//gateway-ip` has
  selector `['ip']` and result `['ip']`; `ip` is not an op (elsewhere it is a
  protocol label, rows 49–54) and the gateway is `28.239.79.65`, so the rule
  never fires. Most plausible readings: typo for `any`/`value`. Not emitted in
  `dsl.expected.txt`.
* **Q3:** `[TABLE|…]` references when the referenced object does not exist in
  the output: skip the field, or emit the name anyway? `dsl.expected.txt`
  assumes skip for *fields* that are pure references (none of its rows use
  them; only rows outside the audited groups do).
* **Q4:** `list_2_string` separator (`comm_range`); `ocvalue_range_ge/le` split;
  `"empty_dict"` ockey branch; `{|ockey=…}` brace grammar — all only lightly
  exercised or unexercised in this document.
* **Q5:** `string_combination` join separator assumed `,` (rows 615/616 give a
  single value; rows 698/699 produce a 32-element comma string). A space-joined
  alternative is possible.
* **Q6:** boolean-ish constants: rows 199/386/448/733/734 map `true/false`
  to `"True"/"False"` (capitalised) whereas rows 73/84/135 map to `up/down` and
  row 308 to `True/False`. Emission is verbatim from `sonic_value`; no
  normalisation.
* **Q7:** row 493's `{|ockey=…}` key syntax is outside the audited groups; the
  proposed grammar is in §6.
