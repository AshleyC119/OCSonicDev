# DSL decision log — every distinct value shape decoded (task-1, dsl-analyst)

Source: `references/raw/yang2sonic_maptable(1).csv` (769 data rows),
`data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt` (15 roots, 4335 string
leaves). Row indexes are 0-based data rows. Machine-checked inventory:
54 distinct `yang_value` literals, 78 distinct `sonic_value` literals (107
distinct leaf tokens), 16 distinct structural nesting shapes.

Confidence: **H** = pinned by ≥2 independent rows and verified against the OC
document; **M** = pinned by one row or verified only structurally; **L** =
inferred from naming/deduction, unexercised by this document.

Full rules: `docs/dsl-semantics.md`. Contract corrections are in that file §9.

---

## A. `yang_value` selector shapes (all 54 distinct literals)

### A.1 Ops (always-match selectors)

| literal | n | rows (examples) | decoding | conf |
|---|---|---|---|---|
| `[['unchanged']]` | 519 | 10,11,18,119,134 | pass leaf value | H |
| `[['empty_dict']]` | 32 | 82,160,169,256,438,756 | presence rule: emit key/field as `{}` | H |
| `[['any']]` | 26 | 23–54 | match anything; paired with `NONE` result (emit nothing) | H |
| `[['list_value']]` | 12 | 400,402,423,444 | leaf is a list; emit JSON list | M |
| `[['combination']]` | 11 | 64,70,121,187,494,613,649 | scalar template from bindings (`ADDRESS+/+value`, `INTERFACEID`, `GROUP`, `AREA`, `ACL-SET`, `COMMUNITY`) | H |
| `[['default']]` | 10 | 2,6,60,72,196 | constant candidate (branch 0) | H |
| `[['default']],[['default']]` | 10 | 0,1,58,59,419,426 | 2 targets, constant each | H |
| `[['default']],[['list_combination']]` | 10 | 98–100,112–114,150–152 | constant + JSON-list field | H |
| `[['NONE']]` | 7 | 69,74,76,78,79,118,156 | suppression (§3.3 of semantics) | H |
| `[['compute']]` | 5 | 3,5,7,138,144 | transform of leaf value | H |
| `[['string_combination']]` | 3 | 374,615,616 | comma-joined accumulation | M |
| `[['true']]` | 3 | 137,427,633 | single-value enumeration (fires only when leaf == `"true"`) | H |
| `[['ALL']]` | 2 | 8,9 | literal label `"ALL"` | H |
| `[['list_combination']]` | 2 | 61,348 | JSON-list field (no expansion) | H |
| `[['list_2_string']]` | 2 | 656,657 | list → joined string | M |
| `[['lowercase']]` | 1 | 674 | lower-case leaf value | H |
| `[['ockey', path], ['ocvalue']]` | 2 | 71,77 | ockey lookup; emit looked-up value | H |
| `[['ockey', path], ['combination_ocvalue']]` | 1 | 614 | ockey lookup; looked-up value feeds reference template | M |
| `[["ockey", path], ["combination_ocvalue"]]` (row 668 target 2) | 1 | 668 | same as 614 | M |

### A.2 Enumerations (label index selects candidate)

| literal | n | rows | decoding | conf |
|---|---|---|---|---|
| `[['true','false']]` | 42 | 73,84,91,105,135,199 | `true`→cand0, `false`→cand1 | H |
| `[['OSPF','OSPF6','default']]` | 6 | 399,403,405,471,475,477 | redistribute protocol→`ospf/ospf6/connected` | H |
| `[['permit','deny']]` | 6 | 12–17 | forwarding-action→ACCEPT/DROP/FORWARD | H |
| `[['udp','tcp','ip']]` | 6 | 49–54 | ip protocol→`17/6/NONE` (note `NONE` = omit field) | H |
| `[['ACCESS','TRUNK','route']]` | 3 | 101,115,153 | interface-mode→`access/trunk/none` (**casing trap**, §D.5) | H |
| `[['ACL_IPV4','ACL_IPV6','ACL_CTRL']]` | 3 | 65,66,67 | acl type→`L3/L3V6/CTRLPLANE` | H |
| `[['FAST','SLOW']]` | 2 | 161,165 | lacp interval→`true/false` | M |
| `[['KERNEL','OSPF','OSPF6','default']]` | 2 | 401,473 | redistribute protocol→`kernel/ospf/ospf6/connected` | H |
| `[['SNMP-Filter','SSH-Filter']]` | 2 | 62,63 | acl name→policy_desc | H |
| `[['STATIC','LACP']]` | 2 | 96,110 | lag-type→`static/NONE` | M |
| `[['ACCEPT_ROUTE','REJECT_ROUTE']]` | 1 | 658 | policy-result→`permit/deny` | H |
| `[['INFORMATIONAL','INFO']]` | 1 | 255 | syslog severity→`notice/info` | H |
| `[['none','fec','rs-fec']]` | 1 | 143 | fec mode→`none/fc/rs` | H |
| `[['rx','tx','all','none']]` | 1 | 672 | lldp admin-status→`rx-only/tx-only/rx-and-tx/disabled` | H |
| `[['ip']]` | 1 | 68 | **anomaly**: `ip` is not an op; see §D.1 | L |

### A.3 Multi-target ockey selectors

| literal (abridged) | n | rows | decoding | conf |
|---|---|---|---|---|
| `[[ockey monitor-link up-delay, ['ocvalue']], ['default'], ['combination'], ['default']]` | 6 | 187,188,190,191,193,194 | updelaytime from group up-delay; linkmode/groupid/option constants | H |
| 2-target Loopback port! `[[ockey index, ['0','1','ockey_default']], [ockey vrf-enable-prev, ['empty_dict','ockey_default']]]` | 1+1 | 88,89 | type primary/secondary/default; second target = interface presence `{}` or `NONE` | H |
| prefix-set 7-target ockey (ocvalue & ocvalue_range_ge/le) | 1+1 | 666,667 | BGP_IPPREFIXLIST fields; **never fires here** | M |
| bgp-access-list 4-target ockey | 1 | 668 | BGP_ACCESSLIST fields; never fires | M |
| community-set 4-target (`combination`, 2×ocvalue ockey, ockey+`default`) | 1 | 649 | BGP_COMMS fields | H |
| `[['ockey', static-nh path], ['ocvalue']]` (single target, unwrapped form) | 2 | 71,77 | MGMT gwaddr | H |
| 4/8-target heterogeneous (`unchanged/combination/default`, `default×3+string_combination+…`) | 1+1+2+1 | 157,659,698,699,257,612,418 | see semantics §4 | H |

## B. `sonic_value` result atoms (all 107 distinct leaf tokens)

### B.1 Sentinels / ops

| token | n | rows | emission | conf |
|---|---|---|---|---|
| `NONE` | 43 | 23–54,69,74,… | do not emit | H |
| `empty_dict` | 34 | 82,160,256,438 | emit `{}` (2-segment key or key-only presence) | H |
| `unchanged` | 527 | 10,119,134 | leaf value | H |
| `value` | 3 | 61,615,616 | leaf value (or list element) | H |
| `ocvalue` | 13 | 71,187,649,… | looked-up ockey value | H |
| `lowercase` | 1 | 674 | lower-cased leaf | H |
| `list_value` | 12 | 400,423,444 | leaf list as JSON list | M |
| `list_2_string` | 2 | 656,657 | leaf list joined `,` (separator unverified) | M |
| `ocvalue_range_ge` / `ocvalue_range_le` | 2+2 | 666,667 | split `masklength-range` (unexercised) | L |

### B.2 Transforms (only with `compute`)

| token | n | rows | decoding | conf |
|---|---|---|---|---|
| `original//1000` | 2 | 138,144 | integer division: 200000000→200000, 2000→2 | H |
| `10000-original` | 3 | 3,5,7 | `10000-sec`: 10→9990 | H |
| `log2(original)` | 2 | 677,681 | `int(log2(v))`: 8→3 | M |

### B.3 Templates (`+` concatenation with bare variable names)

`ADDRESS+/+value` (70), `PortChannel+INTERFACEID` (98–100,112–114),
`IPADDR+:+PORT` (374), `GROUP` (187–194), `INTERFACE` (150–152,698,699),
`INTERFACEID` (121), `NEIGHBOR` (418,461), `AREA` (494,546), `COMMUNITY` (257),
`SERVER` (254,348), `SUBINTERFACE` (157), `PREFIX` (668), `DEFINITION` (659),
`VALUE_LIST` (649), `ACL-SET` (64),
`[SCHEDULER|scheduler.+ocvalue+.+value+]` (614), `[BUFFER_PROFILE|…+INTERFACE+_+QUEUEID+]`
(677,680,681), `[+value+]`/`[WRED_PROFILE|+value+]`/`[EBST_PROFILE|+value+]` (613,617,745,749,768).
All conf H except the reference fallback rule (M).

### B.4 Reference expressions `[TABLE|key-template]`

`[DSCP_TO_TC_MAP|global-dscp2tc-profile]`, `[…|default]`, `[TC_TO_QUEUE_MAP|…]`
(612, 2 alternatives per branch → fallback chain), `[WRED_PROFILE|+value+]` (613),
`[EBST_PROFILE|+value+]` (617), `[BUFFER_POOL|egress_lossy_pool]` /
`[BUFFER_POOL|ingress_lossy_pool]` (677,681), `[BUFFER_PROFILE|…]` (677,680,681),
`[SCHEDULER|…]` (614). Decoding: emit the **key part** as the field value and
record the referenced object (dependency); a one-branch multi-item list is a
priority list of alternatives. conf M-H (verified empirically: document really
produces `SCHEDULER|scheduler.DWRR.50`,
`BUFFER_PROFILE|egress_profile_Eth400GE27_5`, `DSCP_TO_TC_MAP|global-dscp2tc-profile`).

### B.5 JSON list constants

`['SNMP']`/`['SSH']`/`['']` (services/ports, 58/59) and `['PORTS']` (698/699)
are one-element lists nested inside the candidate ⇒ emitted as JSON arrays; some
other one-element candidates (`['2048']`, `['ALL']`, `['1']`, …) are scalars.
The only reliable discriminator is the extra nesting level in the literal, see
semantics §2.

### B.6 Constants (pass-through strings)

`0`,`1`,`2`,`2048`,`9999`? no — observed: `10000`,`8999`,`17`,`2048`,`ALL`,`ACCEPT`,
`DROP`,`FORWARD`,`L3`,`L3V6`,`CTRLPLANE`,`INGRESS`,`IFA_INGRESS`,
`INTINGRESSPASS2`,`up`,`down`,`enable`,`disable`,`True`,`False`,`true`,`false`,
`primary`,`secondary`,`tagged`,`untagged`,`access`,`trunk`,`none`,`static`,
`standard`,`permit`,`deny`,`activate`,`no-activate`,`bfd`,`add`,`uplink`,
`downlink`,`notice`,`info`,`public`,`tacacs+`,`tacacs+,local`,`ecn_all`,
`rx-only`,`tx-only`,`rx-and-tx`,`disabled`,`fc`,`rs`,`ingress`,`kernel`,`ospf`,
`ospf6`,`connected`,`SNMP`,`SSH`,`PUBLIC`? (no). All conf H (literal copy; note
`tacacs+,local` must not be split on `+`).

## C. Structural nesting shapes (all 16 `(yv-sig, sv-sig, ntargets)`)

| shape (schematic) | n | example rows | normalisation |
|---|---|---|---|
| `[[s]] / [[s]]` n=1 | 636 | 2,10,119 | selector `[s]`, cands `[s0]` |
| `[[s,s]] / [[s,s]]` n=1 | 56 | 73,135 | enumeration |
| `[[[s]],[[s]]] / [[[s]],[[s]]]` n=2 | 26 | 0,58,419 | strip one wrapper on both sides |
| `[[s,s,s]] / [[s,s,s]]` n=1 | 19 | 65,101,143 | enumeration |
| `[[[s,s],[s]],[[s]],[[s]],[[s]]]` n=4 | 6 | 187–194 | ockey pair + wrapped constants |
| `[[s,s],[s,s,s]] / [[s,s,s]]` n=1 | 5 | 120,71(3 rows),102 | single ockey spec written unwrapped |
| `[[s,s],[s]] / [[s]]` n=1 | 4 | 71,77,120,154 | same |
| `[[[s]],[[s]],[[s]]]` n=3 | 3 | 157, 677, 681 | wrapped singletons (157 also has `combination`/`default`) |
| `[[[s]],[[s]]] / [[[[s]]],[[[s]]]]` n=2 | 2 | 58,59 | extra level = JSON list values |
| `[[[s,s],[s,s,s]],[[s,s],[s,s]]]` n=2 | 2 | 88,89 | ockey pairs (one with default labels) |
| 7×`[[ockey],[ocvalue]]` n=7 | 2 | 666,667 | unwrapped ockey specs |
| 8 wrapped singletons n=8 (sv double-nested) | 2 | 698,699 | one target list-valued |
| mixed 4-target shapes | 3 | 157,649,668 | per-target normalisation |
| `[[[s]],[[s]]] / [[[s,s]],[[s,s]]]` n=2 | 1 | 612 | long candidate list = fallback |
| mixed 3–4 target shapes | 2 | 659,257,418 | per-target normalisation |

Noise rules a parser must implement: unwrap single-element list wrappers on the
selector side; unwrap exactly one wrapper level on the candidate side; do not
confuse the resulting wrapper with a JSON-list value (it is one level deeper).

## D. Inconsistencies, typos and traps found in the CSV

1. **Row 68**: `['ip']` selector / `['ip']` result for
   `interfaces//interface//BMC//bmc//config//gateway-ip`. `ip` is not an op, and
   the doc gateway is `28.239.79.65`, so under strict matching the rule never
   fires. Most plausible intent: selector `any`/`value`, result `value`
   (`BMC|INTERFACE|defgw = "28.239.79.65"`). The line is included in
   `audit/dsl.expected.txt` marked `ASSUMED`; the current engine output already
   emits it. Also note the key component `INTERFACE` in rows 68/70 is a
   **literal**, not `$INTERFACE$`.
2. **Literal interface-name casing**: rows 82/83/84/86 use `LoopBack…` (capital B)
   but the document has `Loopback0`, so they never fire; rows 85/87/88/89
   (`Loopback…`) do. Exactly the reverse for row 68/69 (`BMC`).
3. **`port-channel` vs `Bridge-Aggregation`**: rows 104–117 address a lowercase
   `port-channel…` interface name that this document does not contain; the doc
   uses `Bridge-AggregationN`, covered by rows 90–103 (and by rows 160/161/
   164/165 for LACP members). Both variants map to the same SONiC tables, so
   they are aliases for two device families, not duplicates.
4. **Casing trap (high impact)** is item 5 below.
5. **Casing trap (high impact)**: rows 101/115/153 selectors are
   `['ACCESS','TRUNK','route']`; the document stores lowercase `"trunk"` for all
   16 Bridge-Aggregations and `"route"` for the 24 routed Ethernet ports. Exact
   matching drops `PORTCHANNEL|PortChannelN|switchmode` (row 101) while row 153
   works; case-insensitive matching adds 16 `switchmode = "trunk"` lines.
   Only this family is affected (checked over all 4335 leaves).
6. **Exact duplicate rows**: 206/207 (`system//config//role`), 259/264
   (`system//counter//buffer-pool//config//enable`), 278/283
   (`…//poll-interval`). Idempotent; no action needed.
7. **`$VALUE_LIST$` in key vs `combination` selector** (row 649): the selector
   says `combination` although the leaf is a list; expansion is driven by the
   key placeholder, not by the selector. Same for rows 98–100/150–152 which use
   `list_combination` only for the *second* target while the first target's key
   also expands.
8. **Literal `permit` in row 649 keys** although `opt_type` comes from
   `forwarding-action` (which could be `deny`): keys are always
   `BGP_COMMS|<set>|permit|<member>`. Faithful reading keeps the literal.
9. **`$VALUE` without closing `$`?** none; but `$VALUE${|ockey=…}` (row 493) is
   the only brace syntax and must survive `//` splitting.
10. **`$SCHEDULAR$` (rows 629–632) vs `$SCHEDULER$` (row 614)**: different
    spellings for the same role, both only in key/selector paths.
11. **Missing selectors**: rows 61 (`list_combination`+`value` for a scalar
    `"VLAN"`) and 254 (`servers` list) rely on op semantics rather than shape.
12. **`0`/`1` result constants vs `True`/`False`**: rows 385/392/419/432 map
    booleans to `"1"/"0"`, rows 199/386/448/733/734 to `"True"/"False"`, rows
    73/84/135 to `up/down`, rows 259… to `enable/disable`. Verbatim emission;
    no global normalisation is justified by the table.
13. **Spine labels are not table names**: 56 of 72 spines are OC roots
    (e.g. `network-instances//network-instance`) even when the emitted tables are
    BGP_*/STATIC_ROUTES; 16 spines are SONiC-ish names (DEVICE_METADATA,
    SYSTEM_PORT, BUFFER_*, PBR_*, BGP_VRF*). A matching rule uses `yang_key`
    only; spines are grouping only.

## E. `audit/dsl.expected.txt` provenance and coverage

626 lines, table-sorted by `(table, key, field)`, contract §5 format
`TABLE|KEY|FIELD = <json>  # r<row> <OC path>`. Scope: rules 68–157
(`interfaces//interface`, all 90 rows), 187–195 (`system//monitor-link`), and
649/666/667/668 (`routing-policy//defined-sets`). Tables produced:
PORT 368, PORTCHANNEL 192, BGP_COMMS 36, VLAN_MEMBER 16, VLAN 6, VLAN_INTERFACE
3, BMC 2 (one marked `ASSUMED`, §D.1), LOOPBACK/LOOPBACK_INTERFACE/MGMT_INTERFACE
1 each. At the time of writing all 626 lines matched
`outputs/CQ-JLDC-2203-D05-TCS84R-LA200G-019.sonic.json` exactly, and the engine
did not create the tables/keys listed as expected absences below.

It is the output of a scratch reference implementation of this decoded DSL
(kept outside the repo), with the following lines verified by hand against the
document: PORT|Eth400GE27|* (all 13 fields), PORTCHANNEL|PortChannel13|* (12),
VLAN|Vlan2|* (6), the 3 VLAN_INTERFACE addresses, LOOPBACK_INTERFACE,
LOOPBACK, MGMT_INTERFACE, BMC, VLAN_MEMBER|Vlan2|PortChannel13, and the
`BGP_COMMS|10|permit|1:1` group. Every line carries the rule row and OC path;
independent re-derivation is expected from those comments.

Expected *absences* worth diffing: no `PORT` entries for `eth0`, `BMC`, `Vlan2`,
`Loopback0`, `Bridge-AggregationN` (suppressed/outranked), no `INTERFACE` or
`VLAN_SUB_INTERFACE` table at all (rows 154/155 outranked, 156/157 leaves
absent), no `BGP_IPPREFIXLIST`/`BGP_ACCESSLIST` (rows 666/667/668 cannot match),
no `MGMT_VRF_CONFIG` (row 72: no interface vrf leaf), no `PORTCHANNEL|…|mode`
(rows 96/110: no `lag-type`). Fields added to the same keys by rules outside my
scope (e.g. `PORT|…|lldp_status` from row 672, `VLAN|Vlan2|gw_ip`/
`dhcp_servers` from rows 158/159) are intentionally not part of this file.

`VLAN|Vlan2|members` is accumulated in **document order**:
`PortChannel13,14,15,16,1,4,5,2,3,8,9,6,7,10,11,12` (the order the
Bridge-Aggregation interfaces appear in the OC document). An implementation that
sorts the list is semantically equivalent but will not diff byte-wise.
`PORTCHANNEL|…|switchmode` is absent for the reason in §D.5; if the Lead adopts
case-insensitive enum matching, add 16 lines
`PORTCHANNEL|PortChannelN|switchmode = "trunk"  # r101 interfaces/interface/Bridge-AggregationN/aggregation/switched-vlan/config/interface-mode`.
