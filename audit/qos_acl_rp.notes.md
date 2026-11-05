# task-4 audit — acl / qos / routing-policy / lacp / lldp / int / mqc-acl / vxlan

Auditor: qa-auditor. Inputs: `references/raw/yang2sonic_maptable(1).csv` (769 data rows, 0-based),
`data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt`.
Owned rows: **147** = `acl//acl-sets` 68, `qos//global` 11, `qos//wred-policies` 10,
`qos//scheduler-policies` 6, `qos//interfaces` 6, `qos//car-policies` 4, `qos//ebst-policies` 2,
`routing-policy//defined-sets` 7, `routing-policy//policy-definitions` 16, `lacp//interfaces` 8,
`lldp//interfaces` 1, `int//interfaces` 2, `mqc-acl//acl-sets` 4, `vxlan//evpn` 1, `vxlan//tunnels` 1.
Row indexes below are CSV data-row indexes (header excluded), the same numbering as the contract.

Result: **69 rows emit, 28 rows fire but emit nothing (all candidates are `NONE`), 50 rows do not
match this document.** 885 expected emission lines, 15 SONiC tables — see `qos_acl_rp.expected.txt`.

Method: an independent mini-implementation of the contract's matching + value DSL, written from the
CSV and OC document only (temporary script, not part of `translator/`). Its 885 lines were then
compared against the Lead engine's output restricted to these 147 rows: **identical, 0 differences**.
The cross-checks that make me trust the derivation are listed at the end.

---

## 1. Answers to the two required questions

### 1.1 Is `1000` in the ACL yang_key a literal OC entry or a synthetic default rule?

**Literal OC entry id — and yes, `DEFAULT_RULE` entries with PRIORITY `"1"` are emitted for all
three acl-sets in this document.**

Evidence:

* The document really contains an entry whose id is `1000` in every acl-set, e.g.
  `acl/acl-sets/acl-set/SNMP-Filter ACL_CTRL/acl-entries/acl-entry/1000` with
  `config/sequence-id = "1000"`, `actions/config/forwarding-action = "deny"`, and also a duplicate
  direct `sequence-id = "1000"` leaf next to `config/`. Same layout for `SSH-Filter ACL_CTRL`
  (entry 1000) and `2000_IVLAN ACL_IPV4` (entry 1000 is the last of its 13 entries).
* Therefore rows 0,1,2,4,12,14,23,25,30,32,37,39,43,45,49,51,55,56 (the literal-`1000` rows) match
  **real leaves**, they are not a presence/empty-marker rule. Rows 0/1 additionally match the
  *direct* `<entry>/1000/sequence-id` leaf (that is why the ETHER_TYPE/IN_PORTS constants hang off a
  `sequence-id` pattern).
* The table maps that entry to SONiC's conventional deny-all rule `DEFAULT_RULE` with PRIORITY `1`
  (rows 6/16/55/56 and the literal rows). Emitted here:
  * `ACL_RULE|SNMP|DEFAULT_RULE` = PRIORITY "1", PACKET_ACTION "DROP", ETHER_TYPE "2048", IN_PORTS "ALL"
  * `ACL_RULE|SSH|DEFAULT_RULE`  = the same four fields
  * `ACL_RULE|2000_IVLAN|DEFAULT_RULE` = PRIORITY "1", PACKET_ACTION "DROP", ETHER_TYPE "2048", OUT_VLANID "Vlan2"
* **`RULE_1000` is NOT emitted.** At *every* leaf of the entry-1000 object the literal-1000 rules are
  strictly more specific than the generic `$ACL-ENTRY$` rules, so the defaults win the leaf and the
  entry never gets a `RULE_1000` mapping:
  - SNMP/SSH `.../1000/config/sequence-id`: row 2/4 (9 literal segments) beats row 3/5 (8 literal +
    `$ACL-ENTRY$`) and row 6 (8 literal); the *direct* `.../1000/sequence-id` leaf is only matched
    by rows 0/1.
  - `.../1000/{ipv4,transport,actions,l2}/...`: literal SNMP/SSH rows (9 literal segments) and the
    generic 1000 rows (8) both beat rows 24/31/38/44/50/54/57 (7 literal segments).
  - `2000_IVLAN .../1000/...`: generic-1000 rows 6,16,27,34,41,47,53,55,56 (8 literal segments) beat
    rows 7,17,28,35,42,48,54,57 (7).
* Robustness: *three* independent decision rules give the same answer for the ACL block —
  (a) max literal specificity, (b) "first matching row in CSV order wins", (c) the CSV's own
  literal-before-generic ordering. So the DEFAULT_RULE-only conclusion does not depend on the
  specificity tie-break.
* Risk if the Lead changes to "apply every matching rule with last-write-wins": `RULE_1000`
  (PRIORITY 9000/9000/9000, PACKET_ACTION DROP, and OUT_VLANID "Vlan2" for 2000_IVLAN) would
  additionally appear for all three sets. I recommend against that; it duplicates DEFAULT_RULE.

### 1.2 How does `$ACL-SET$ $TYPE$` bind, and is the ACL_TABLE key the set name or "name type"?

* The OC acl-set object key is `"<name> <type>"` (`2000_IVLAN ACL_IPV4`, `SNMP-Filter ACL_CTRL`,
  `SSH-Filter ACL_CTRL`), and the object repeats that string in the synthetic `name,type` leaf, plus
  `name` = `2000_IVLAN` / `SNMP-Filter` / `SSH-Filter` and `type` = `ACL_IPV4` / `ACL_CTRL`.
* `$ACL-SET$ $TYPE$` splits the key at the space: `ACL-SET = 2000_IVLAN | SNMP-Filter | SSH-Filter`,
  `TYPE = ACL_IPV4 | ACL_CTRL`. (`SNMP-Filter ACL_CTRL` ⇒ ACL-SET=SNMP-Filter, TYPE=ACL_CTRL —
  the contract's example is correct.) Names here contain no space, so greedy vs lazy does not matter.
* **The SONiC key is the name part only, never the full "name type" string.** The generic rows only
  ever use `$ACL-SET$` (`ACL_TABLE//$ACL-SET$//stage`, `ACL_RULE//$ACL-SET$|RULE_$ACL-ENTRY$//...`),
  producing `ACL_TABLE|2000_IVLAN` and `ACL_RULE|2000_IVLAN|RULE_*`.
* The key is whatever the rule row supplies, not the raw OC name string: for the two filter sets the
  literal rows 58/59/62/63/65/66/0/1/2/4/… emit the short keys `SNMP`/`SSH`, which are *not* the OC
  `config/name` (`SNMP-Filter`, `SSH-Filter`). So `ACL_TABLE` keys here are
  `SNMP`, `SSH`, `2000_IVLAN`, `IFA_INGRESS` and every `ACL_RULE` key uses the same name as its
  `ACL_TABLE` key prefix (`SNMP|RULE_10`, `SNMP|DEFAULT_RULE`, `2000_IVLAN|RULE_500`,
  `2000_IVLAN|DEFAULT_RULE`, …).

---

## 2. DSL readings used, and corrections to `docs/ENGINE_CONTRACT.md`

The contract is a good spec; these are the places where it is silent or where I read the CSV
differently. All were validated against this document (and agree with the current engine).

| # | Contract point | Correction / completion | Evidence |
|---|---|---|---|
| C1 | §2.1/§3.1 nesting of `yang_value`/`sonic_value` | Multi-target rows wrap **each** target's selector and candidate list in one extra list level; single-target rows do not; `ockey` selectors are never wrapped. Parser must handle `[[['default']], [['default']]]` (2 targets) vs `[['default']]` (1 target) and `[[['ockey',p],['ocvalue']], …]`. | row 0 vs row 2; rows 636, 649, 58 |
| C2 | §2.2 "largest number of literal segments" | Any monotone specificity works on this doc: max-literal-segments, max-literal-characters (what the engine uses) and first-match-in-CSV-order all pick the same winner for all 147 rows. No tie occurs here. | rows 2/3/6, 4/5/6, 62/64, 65/67 |
| C3 | §3.2 "`list_combination` without `$VALUE_LIST$` ⇒ emit the raw string as one value" | The DSL type means **collect**: one element per matched leaf, emitted as a JSON list (`ACL_TABLE|2000_IVLAN|ports = ["VLAN"]`, not `"VLAN"`). `ACL_TABLE.ports/services` are lists everywhere else in this group (rows 58/59 emit `["SNMP"]`), so a list is the consistent shape. | row 61; rows 348/254 use the same type to collect DNS/syslog servers |
| C4 | §3.3 `sonic_value` candidates (silent about `[TABLE|KEY]`) | A bracketed candidate is a **foreign-key reference: emit KEY only** (drop `TABLE|`). `[SCHEDULER|scheduler.+ocvalue+.+value+]` must yield `scheduler.DWRR.50` = the `SCHEDULER` key built by rows 629/630; same for `[WRED_PROFILE|…]`, `[EBST_PROFILE|…]`, `[BUFFER_PROFILE|…]`, `[BUFFER_POOL|…]`, `[DSCP_TO_TC_MAP|…]`, `[TC_TO_QUEUE_MAP|…]`. | rows 612–614, 617, 677/680/681, and 629/630 |
| C5 | §3.3 (silent about `string_combination`) | `string_combination` **accumulates over all matches of the rule and comma-joins** them (dedup, document order). With one match it is just the value. | rows 698/699 (32 interfaces → one comma list), 615/616 (single) |
| C6 | §3.1 selector table | `yang_value` may also be a bare branch list of literal OC values with no value remap (rows 8/9 `['ALL']`, row 672 `['rx','tx','all','none']`), i.e. "value must equal one of these and candidate index = position". | rows 8, 9, 672 |
| C7 | §5 line format | Confirmed: 2-segment templates (`PORTCHANNEL_MEMBER//key`) produce no field part; format `TABLE|KEY = {}`. Only 16 such lines here. | rows 160 |
| C8 | §6 open questions 1 & 2 | Answered in §1.1/§1.2 above. | — |
| C9 | §2.2 note "spine names a table the document does not contain" | The 12 dead rows fail because the **OC** subtree is absent from this document (`mqc-acl` 4 rows, `vxlan` 2, `qos//ebst-policies` 2, `qos//car-policies` 4), not because of spine/table filtering. | rows 183–186, 643–648, 700–701 |

Also correct the contract's §3.1 claim that `['default']` is a "constant branch: always candidate 0":
that is true, but the rule only fires if its `yang_key` matches a real leaf — `['default']` is not a
presence test. (E.g. rows 8, 26x etc. stay dead for this document.)

---

## 3. Emission inventory (what this group contributes to the reference JSON)

| SONiC table | lines | keys | fields emitted |
|---|---|---|---|
| ACL_RULE | 143 | 51 | ETHER_TYPE, IFA_VERSION, IN_PORTS, IP_PROTOCOL, OUT_VLANID, PACKET_ACTION, PRIORITY |
| ACL_TABLE | 16 | 4 | services, ports, stage, policy_desc, type |
| BGP_COMMS | 36 | 9 | comm_number, list_number, mode, opt_type |
| BGP_ROUTEMAPS | 60 | 13 | applycost, comm_range, matchcommunity, name, opttype, prefix_name, seqnumber |
| DSCP_TO_TC_MAP | 64 | 1 (`global-dscp2tc-profile`) | dscp 0…63 → tc |
| TC_TO_QUEUE_MAP | 8 | 1 (`global-tc2queue-profile`) | tc 0…7 → queue |
| SCHEDULER | 12 | 6 (`scheduler.DWRR.{0,1,3,20,25,50}`) | type, weight |
| WRED_PROFILE | 26 | 2 (`100GE_queue_5`, `200GE_queue_5`) | 13 fields each (ecn, red/yellow/green min/max/prob + wred_*_enable) |
| QUEUE | 288 | 256 (32 ifaces × 8 queues) | scheduler (all), wred_profile (32 × queue5) |
| PORT_QOS_MAP | 96 | 32 | dscp_to_tc_map, tc_to_queue_map, pfc_enable |
| PFC_WD_TABLE | 36 | 33 (GLOBAL + 32 ports) | action, poll_interval, restoration_time5, detection_time5, pri_enable |
| PFC_WARNING_CONFIG_TABLE | 4 | 1 (CONFIG) | poll_time, speed_threshold, suppression_num, suppression_time |
| PORTCHANNEL | 48 | 16 (PortChannel1…16) | fast_rate, fallback, port_id_basic |
| PORTCHANNEL_MEMBER | 16 | 16 | (empty object) |
| PORT | 32 | 32 | lldp_status |
| **total** | **885** | | |

Per spine (lines): `acl//acl-sets` 151, `qos//interfaces` 416, `qos//scheduler-policies` 84,
`lacp//interfaces` 64, `routing-policy//policy-definitions` 60, `routing-policy//defined-sets` 36,
`lldp//interfaces` 32, `qos//wred-policies` 26, `qos//global` 8, `int//interfaces` 8.

Note on the expected-file comments: lines produced by `list_combination`/`string_combination`
aggregation are emitted once per rule, not once per leaf, so they carry the synthetic path marker
`<list_combination>` / `<string_combination>` instead of one OC path (3 + 32 lines).

Concrete cross-table referential integrity worth checking in the real answer:
`QUEUE|<port>|<q>|scheduler` values are exactly the 6 `SCHEDULER|scheduler.DWRR.<id>` keys;
`QUEUE|…|5|wred_profile` values are the 2 `WRED_PROFILE` keys; `PORT_QOS_MAP` map names are the
`DSCP_TO_TC_MAP`/`TC_TO_QUEUE_MAP` keys; ACL rules sit under `ACL_TABLE` keys `SNMP`, `SSH`,
`2000_IVLAN`, `IFA_INGRESS`.

---

## 4. Per-rule verdicts

### acl//acl-sets — 68 rows: 29 emit / 28 fire-with-no-output / 11 no-match

Emitting rows (lines in parentheses):
`0` (2: ETHER_TYPE, IN_PORTS on SNMP|DEFAULT_RULE), `1` (2, SSH), `2` (1: PRIORITY 1),
`3` (17: SNMP|RULE_10…170 PRIORITY = 10000−seq), `4` (1), `5` (18: SSH|RULE_10…180),
`6` (1: 2000_IVLAN|DEFAULT_RULE PRIORITY 1), `7` (12: 2000_IVLAN|RULE_* PRIORITY),
`12` (1: DEFAULT_RULE DROP), `13` (17: SNMP RULE_* PACKET_ACTION ACCEPT), `14` (1), `15` (18: SSH ACCEPT),
`16` (1: 2000_IVLAN DEFAULT DROP), `17` (12: 2000_IVLAN FORWARD/DROP),
`50` (17: SNMP RULE_* IP_PROTOCOL 17 because every SNMP entry protocol is `udp`),
`54` (4: only 2000_IVLAN entries 70/80/90/100 have protocol `udp` → 17; `ip` maps to `NONE`),
`55` (1: 2000_IVLAN DEFAULT ETHER_TYPE 2048), `56` (1: 2000_IVLAN DEFAULT OUT_VLANID Vlan2),
`57` (12: 2000_IVLAN RULE_* OUT_VLANID Vlan2), `58` (2: services/ports SNMP), `59` (2: SSH),
`60` (1: stage), `61` (1: ports ["VLAN"]), `62` (1: SNMP policy_desc), `63` (1: SSH),
`64` (1: 2000_IVLAN policy_desc "2000_IVLAN"), `65` (1: CTRLPLANE), `66` (1: CTRLPLANE),
`67` (1: 2000_IVLAN type L3).

Fire but no output — every candidate is `NONE` (the CSV deliberately drops these match keys):
`23,25,27,30,32,34,37,39,41,43,45,47` (single = entry-1000 leaves) and
`24,26,28,31,33,35,38,40,42,44,46,48` (17/18/12 per-entry leaves) for destination-address,
source-address, source-port, destination-port; `49,51,53` for protocol on entry 1000 (`ip`→`NONE`);
`52` for SSH protocol (`ip`→`NONE`). Consequence: **no ACL rule in this document gets SRC_IP,
DST_IP, L4_SRC_PORT or L4_DST_PORT**, even though the OC entries carry concrete addresses/ports.

No match (leaf absent in this document): `8,9` (`config/in-ports`), `10` (`config/in-lags`),
`11` (`config/in-subif`), `18` (`actions/config/tc-action`), `19` (`actions/config/tunnel-vni`),
`20` (`actions/config/car-policy`), `21` (ipv4 `dscp`), `22` (ipv6 `dscp`), `29` (ipv6
destination-address — the document has no `ipv6` subtree), `36` (ipv6 source-address).
Also note: the direct `<entry>/sequence-id` leaf is only mapped for entry 1000 of SNMP/SSH; for
entries 10…500 it has **no** covering rule (harmless, it duplicates `config/sequence-id`).

### qos//global — 11 rows: 8 emit / 0 no-output / 3 no-match

Emit: `618` poll_interval "10", `619` action "forward", `620` restoration_time5 "10",
`621` detection_time5 "10" (PFC_WD_TABLE|GLOBAL), `622` poll_time "10", `623` speed_threshold "1000",
`624` suppression_time "30", `625` suppression_num "5" (PFC_WARNING_CONFIG_TABLE|CONFIG).
No match: `626,627,628` — `qos//global//ebst` is absent from the document.

### qos//wred-policies — 10 rows: 10 emit / 0 no-match

All ten fire on the two policies `100GE_queue_5`, `200GE_queue_5`:
`633` ecn→`ecn_all` (2 lines), `634` red_min_threshold, `635` red_max_threshold,
`636` red_drop_probability + wred_red_enable "true" (4), `637` yellow_min_threshold,
`638` yellow_max_threshold, `639` yellow_drop_probability + wred_yellow_enable (4),
`640` green_min_threshold, `641` green_max_threshold, `642` green_drop_probability +
wred_green_enable (4). 26 lines total. `config/name` and `config/weight` are not covered.

### qos//scheduler-policies — 6 rows: 4 emit / 2 no-match

`610` dscp-tc local-priority → `DSCP_TO_TC_MAP|global-dscp2tc-profile|<dscp 0…63>` (64 lines; field
name is the scheduler id = dscp, value = local-priority = tc). `611` tc-queue qid →
`TC_TO_QUEUE_MAP|global-tc2queue-profile|<tc 0…7>` (8). `629` scheduling-algorithm and `630` weight
→ `SCHEDULER|scheduler.DWRR.<0,1,3,20,25,50>` (6 + 6). No match: `631,632`
(`two-rate-three-color` absent).

### qos//interfaces — 6 rows: 5 emit / 1 no-match

`612` trust-dscp "true" → `PORT_QOS_MAP|<iface>|dscp_to_tc_map = "global-dscp2tc-profile"` and
`tc_to_queue_map = "global-tc2queue-profile"` (64); `613` queue5 wred-policy →
`QUEUE|<iface>|5|wred_profile = "200GE_queue_5"` (32); `614` queue scheduler-policy →
`QUEUE|<iface>|<queue>|scheduler = "scheduler.DWRR.<seq>"` (256); `615` input queue pfc-deadlock →
`PFC_WD_TABLE|<iface>|pri_enable = "5"` (32); `616` input queue pfc →
`PORT_QOS_MAP|<iface>|pfc_enable = "5"` (32). All 32 interfaces have the identical shape
(8 output queues, one input queue5). No match: `617` (`ebst` absent).

### qos//car-policies (645–648), qos//ebst-policies (643–644) — no match

`qos//car-policies` and `qos//ebst-policies` do not exist in the document.

### routing-policy//defined-sets — 7 rows: 1 emit / 6 no-match

`649` fires for community-sets `10` and `20`: per member, `BGP_COMMS|<set>|permit|<member>` with
comm_number = member, list_number = community-set-name, opt_type = forwarding-action ("permit"),
mode = "standard" → 9 keys, 36 lines.
No match: `666` (`$SET$IPv6` prefix sets absent), `667` (**no `config/sequence-id` leaf exists under
`prefixes/prefix`** in this document, so even the two defined prefix-sets `Host-Route` and `LOOPBACK0`
produce nothing — see open question Q-PFX below), `668` (no `bgp-access-lists`), `669–671` (no
`zebra-access-lists`).

### routing-policy//policy-definitions — 16 rows: 6 emit / 10 no-match

`650` set-med → `applycost` (8 statements have set-med 1000); `656` set-community inline →
`comm_range` (8, comma-joined list, single member each here); `658` policy-result →
`opttype = permit|deny` (13); `659` statement `config/name` → `seqnumber` (unchanged, 13) + `name`
(= the policy-definition name, 13); `660` bgp-conditions community-set → `matchcommunity` (4);
`662` match-prefix-set config/prefix-set → `prefix_name` (1: `From-Direct-IPv6|5` →
"LOOPBACK0-IPv6"). Total 60.
No match: `651` set-src, `652` set-local-pref, `653` set-weight, `654` set-as-path-replace,
`655` set-as-path-prepend (all absent from the document), `657` del-community, `661`
prefix-set-ipv6, `663` match-source-prefix-set, `664` call-policy-ipv6, `665` call-policy.

### lacp//interfaces — 8 rows: 4 emit / 4 no-match

`160` member interface leaf (presence, `empty_dict`) → `PORTCHANNEL_MEMBER|PortChannel<N>|<member> = {}`
(16); `161` interval FAST → `fast_rate "true"` (16); `162` edge-port "true" → `fallback "true"` (16);
`163` system-number "1" → `port_id_basic "1"` (16). The doc's 16 `Bridge-AggregationN` interfaces all
have exactly one member and identical config, so the four `port-channel$INTERFACEID$` rows `164–167`
never match (only `Bridge-Aggregation*` keys exist).

### lldp//interfaces — 1 row: 1 emit

`672` admin-status: `all` → `rx-and-tx` (16 interfaces), `rx` → `rx-only` (16);
`PORT|<iface>|lldp_status` → 32 lines. No interface has `tx`/`none`.

### int//interfaces — 2 rows: 1 emit / 1 no-match

`699` (`config/insert-md = "true"`, 32 interfaces) emits
`ACL_RULE|IFA_INGRESS|RULE_1001` = IFA_VERSION "2", PRIORITY "8999", PACKET_ACTION
"INTINGRESSPASS2", IN_PORTS = all 32 interface names comma-joined (string_combination), and
`ACL_TABLE|IFA_INGRESS` = policy_desc "IFA_INGRESS", stage "INGRESS", type "L3", ports `["PORTS"]`
(8 lines).
No match: `698` (`config/insert-md-cloud` absent). Note `698`/`699` target the same key/fields with
PRIORITY 10000 vs 8999, so they were designed to be mutually exclusive per interface.

### mqc-acl//acl-sets (183–186), vxlan//evpn (700), vxlan//tunnels (701) — no match

The document has no `mqc-acl` and no `vxlan` root object (root keys are stp, lldp, bfd,
YANG_VALIDATION, int, default, relay-agent, lacp, acl, network-instances, components, qos,
routing-policy, system, interfaces).

---

## 5. OC paths in my subtrees with no covering rule

Computed over all 769 rows (so these are gaps of the whole table, not just my group); 1157 leaves in
`acl`, `qos`, `routing-policy`, `lacp`, `lldp`, `int` are matched by no rule. The consequential ones:

1. **`acl//interfaces//interface/Vlan-interface2/ingress-acl-sets/ingress-acl-set/TPC-Filter ACL_IPV4`**
   (5 leaves) — the document binds an ingress ACL to a VLAN interface, but the CSV has **no rule at
   all** for `acl//interfaces` (grep: 0 rows). Moreover the referenced set `TPC-Filter ACL_IPV4` is
   not defined under `acl//acl-sets` in this document (only 2000_IVLAN, SSH-Filter, SNMP-Filter), so
   even a generic rule could not fill an `ACL_TABLE` for it. If the reference JSON has a TPC-Filter
   table or an interface→ACL binding, the mapping table cannot produce it — flag for the Lead.
2. `acl//acl-sets//acl-set/<set>` direct leaves `name,type`, `name`, `type` — never emitted (only the
   `config/*` copies are used); `acl-entry/<id>/sequence-id` direct leaf — only entry 1000 of
   SNMP/SSH is mapped (via rows 0/1).
3. **`qos//queues`** (root-level: 8 queues with `name`, `wred/config/enable`, `config/name`) — no rule
   in the whole CSV. The queue table of the reference cannot come from here.
4. `qos//interfaces//interface/<iface>`: `interface-id`, `config/interface-id`, input/output queue
   `name`, and `output/.../scheduler-policy/config/name` (the latter is used only as the `ockey`
   source of row 614, never emitted).
5. `qos//scheduler-policies//scheduler-policy/<policy>`: `name`, `config/name`; dscp-tc scheduler
   `sequence`, `config/sequence`, `conditions/ipv4/config/dscp`; tc-queue `sequence`,
   `config/sequence`; DWRR scheduler `sequence`.
6. `qos//wred-policies//wred-policy/<p>`: `config/name`, `config/weight` ("true" — a nonsense value,
   probably a supplier typo; it is unused).
7. `lacp//config` (`system-number`, `system-id-mac`, `system-priority`) and
   `lacp//interfaces//interface/<agg>/config/s-mlag-group` — no rules (no LACP system / MLAG output).
8. `lldp//config/enabled`, and per interface `config/name`, `config/enabled`,
   `config/management-address` — no rules.
9. `routing-policy`: community-set `community-set-name`/`config/community-set-name` and
   `config/forwarding-action` are used only via `ockey` (not emitted as leaves); policy-definition
   `name`/`config/name` and statement direct `name` are covered indirectly by the pattern, the direct
   leaves themselves are not mapped. Prefix-set prefixes have **no** `sequence-id` leaf (see Q-PFX).

---

## 6. Ambiguities / risks (ranked)

* **A1 (high) `PORTS` keyword.** `int//interfaces` rows 698/699 emit `ACL_TABLE|IFA_INGRESS|ports =
  ["PORTS"]`. This is the *only* place in all 769 rows where the token `PORTS` appears; reading it
  literally gives an invalid SONiC port list, so it almost certainly means "the ports collected by
  this rule". Plausible references: the same 32 interface names as `IN_PORTS`, either as
  `["Eth400GE27", …]` or as one comma string. I kept the literal value in `expected.txt` because
  there is no evidence for the expansion order/shape; **please decide explicitly and record it**.
* **A2 (high) ACL_TABLE `stage` for SNMP/SSH.** Under per-leaf specificity the literal rows 58/59
  (same leaf `acl-set/<set>/config/name` as the generic row 60) win, so `ACL_TABLE|SNMP` and
  `ACL_TABLE|SSH` get `services`, `ports`, `type`, `policy_desc` but **no `stage`**; only
  `2000_IVLAN` and `IFA_INGRESS` get `stage: "INGRESS"`. That is what the CSV says by construction
  and SONiC control-plane tables do not require `stage`; if the reference has it, the fix is to merge
  fields of *different* SONiC field names across specificity levels (+2 lines:
  `ACL_TABLE|SNMP|stage = "INGRESS"`, `ACL_TABLE|SSH|stage = "INGRESS"`).
* **A3 (high) `ACL_TABLE|SNMP|ports` / `|SSH|ports` = `[""]`.** Row 58/59 candidate is `[['']]`
  → a JSON list containing one empty string. Alternative intent: empty list `[]` (SONiC CTRLPLANE
  tables have no ports) or empty string `""`. Same encoding question for `services` (`["SNMP"]` is
  unambiguous).
* **A4 (medium) `IN_PORTS` for `IFA_INGRESS`** is the comma-joined 32 interfaces in document order
  ("Eth400GE27,Eth400GE28,…,Eth200GE10"). Alternative: last-write single value (Eth200GE10) or JSON
  list. Comma-joined matches SONiC's `ACL_RULE.IN_PORTS` format and explains why the CSV uses
  `string_combination` for this target.
* **A5 (medium) `list_combination` shape** (`ACL_TABLE|2000_IVLAN|ports`): I emit the JSON list
  `["VLAN"]`; the written contract says a raw string `"VLAN"`. Only one line differs.
* **A6 (low) PFC field names** `restoration_time5`, `detection_time5` literally append the priority
  id; suspicious, but that is exactly the CSV template. 2 lines.
* **A7 (low) DEFAULT_RULE of `2000_IVLAN` carries `OUT_VLANID = "Vlan2"`** because entry 1000 of that
  set has an `l2/config/outer-vlan`. Semantically odd for a default rule but literal (row 56).
* **A8 (low) `PACKET_ACTION` values differ by rule family**: SNMP/SSH rows map permit→`ACCEPT`
  (rows 13/15) while the generic rows map permit→`FORWARD` (row 17). Exercised here: SNMP/SSH rules
  get ACCEPT, 2000_IVLAN rules get FORWARD. If the reference normalises one of them, 33 lines change.
* **A9 (low) `BGP_COMMS` `list_number` = the community-set *name* ("10"/"20")** and key includes the
  raw member string; this is what row 649 says but it is unusual key composition.
* **Q-PFX (medium, cross-group) BGP_IPPREFIXLIST is empty.** Rows 666/667 need
  `prefixes/prefix/<ip>/config/sequence-id`, which this document does not have (prefix objects only
  carry `ip-prefix`, `masklength-range`, `"ip-prefix,masklength-range"` and their `config/`
  copies). So the two defined prefix-sets produce nothing even though policies reference them
  (`From-Direct-IPv6` statement 5 references `LOOPBACK0-IPv6`, which is not even defined in the
  document). If the reference contains `BGP_IPPREFIXLIST`, the rule's trigger must be the prefix
  *object* (with `$IP$/$MASK$ $RANGE$` bound from the key segment), not the `sequence-id` leaf.
  This is the one place where I suspect the table's trigger leaf and the supplier's real tool differ.

---

## 7. Verification

* Independent re-derivation (not using `translator/`): 885 lines. Engine output restricted to the
  147 rows: 885 lines. Set comparison: **0 lines only in engine, 0 lines only in mine.**
* Internal consistency checks that cross-validate the DSL reading on real values:
  - `QUEUE|<iface>|<q>|scheduler` values (from row 614, template
    `[SCHEDULER|scheduler.+ocvalue+.+value+]`) equal exactly the 6 `SCHEDULER|scheduler.DWRR.*` keys
    built independently by rows 629/630, for all 32×8 queues.
  - `QUEUE|…|5|wred_profile` (32) resolve to the 2 `WRED_PROFILE` keys created by rows 633–642.
  - 32 `PORT_QOS_MAP` keys get `pfc_enable "5"` from the input queue's `pfc/enable`, matching
    `PFC_WD_TABLE|<iface>|pri_enable "5"` from the same queue's `pfc-deadlock/enable`.
  - Every `ACL_RULE` key prefix exists in `ACL_TABLE` (SNMP, SSH, 2000_IVLAN, IFA_INGRESS) and every
    ACL rule has a PRIORITY (9990…9500 for entries, 8999 for IFA, 1 for DEFAULT_RULE).
  - DSCP→TC map produced by row 610 matches the TC values used by `SCHEDULER`/`TC_TO_QUEUE_MAP`
    ranges (0…7).
* Reproduce: `python -m translator --out <tmp>.json --report <tmp>.json` then filter the
  `translate_details.txt` lines by rule index ∈ the 147 row indexes listed above and compare with
  `audit/qos_acl_rp.expected.txt` after stripping the `  # ...` comments.

Files written by this audit: `audit/qos_acl_rp.expected.txt`,
`audit/qos_acl_rp.notes.md`, `audit/qos_acl_rp.summary.json` (nothing else touched).
