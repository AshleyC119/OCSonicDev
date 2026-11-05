# network-instances / multicast / relay-agent audit notes

Auditor: ni-auditor (task-2). Inputs (read-only):
`references/raw/yang2sonic_maptable(1).csv` (769 data rows, 0-based),
`data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt`.

Scope = 244 CSV rows: `relay-agent//dhcp` rows **158,159**; `multicast//l2-mc-groups`
rows **168-170**; `multicast//traffic` rows **171-182**; `network-instances//network-instance`
rows **383-609** (227 rows, contiguous).

Method: flattened the OC document to scalar/list leaves (dict key = one path segment),
compiled every `yang_key` to a placeholder regex (`$NAME$` -> non-empty capture,
literals escaped, repeated names must bind consistently), kept candidates that match the
full path, then applied the contract precedence (largest number of literal segments wins;
CSV order breaks ties; `NONE` suppresses/no-op). Every verdict below was then read against
the concrete leaf and value DSL by hand. 110 leaves exist in my scope; 37 of them match
at least one rule; the other 73 are listed in section 6.

Result: **244 rules -> 20 fire (38 emissions), 18 suppressed by a more specific rule,
206 can never match this document.**

----

## 1. Firing rules and their emissions (20 rules / 38 lines)

`row` = CSV data-row index; all OC paths below are under
`network-instances/network-instance/global/protocols/protocol/BGP BGP/` unless stated.

| row | OC leaf | SONiC emission(s) |
|---|---|---|
| 158 | relay-agent/dhcp/interfaces/interface/Vlan-interface2/config/relay-gateway = "22.215.246.65" (`INTERFACEID`=2) | `VLAN|Vlan2|gw_ip = "22.215.246.65"` |
| 159 | same interface /config/helper-address = 5-element list (`INTERFACEID`=2) | `VLAN|Vlan2|dhcp_servers = [5 IPs]` (see A2) |
| 383 | bgp/global/config/as = "3219" | `DEVICE_METADATA|localhost|bgp_asn = "3219"` |
| 384 | bgp/global/config/router-id = "22.156.39.15" | `BGP_GLOBALCONFIG|bgpGlobal|routeId = "22.156.39.15"` |
| 388 | bgp/global/advertise-delay/config/time = "120" | `BGP_GLOBALCONFIG|bgpGlobal|advertise_delay_value = "120"` |
| 394 | IPv4 advertise-route `$IPADDR$/$IPMASK$`/config/prefix, 4 routes | `BGP_NETWORKS_IPV4|<prefix>|subnet = "<prefix>"` x4 |
| 395 | same routes /config/policy | `BGP_NETWORKS_IPV4|<prefix>|routemap = "<policy>"` x4 (`SetComm-1/1`, `SetComm-1/4`, `SetComm-1/1`, `SetComm-1/1`) |
| 401 | redistribute-route/KERNEL/config/protocol, IPv4 + IPv6 leaves, value "KERNEL" -> enum index 0 -> "kernel" | `BGP_REDISTRIBUTES_IPV4|kernel|protocol = "kernel"`, `BGP_REDISTRIBUTES_IPV6|kernel|protocol = "kernel"` |
| 402 | same KERNEL /config/import-policy (`list_value`) | `BGP_REDISTRIBUTES_IPV4|kernel|routemap = ["From-Direct"]`, `BGP_REDISTRIBUTES_IPV6|kernel|routemap = ["From-Direct-IPv6"]` |
| 407 | IPV4/IPV6 use-multiple-paths/ebgp/config/maximum-paths = "64" | `BGP_CONFIG_IPV4|bgp_ipv4|ebgp_balance = "64"`, `BGP_CONFIG_IPV6|bgp_ipv6|ebgp_balance = "64"` |
| 408 | default-route-distance/config/external-route-distance = "10", both AFIs | `BGP_DISTANCE_IPV4|bgp_ipv4|ebgpdistance = "10"`, `BGP_DISTANCE_IPV6|bgp_ipv6|ebgpdistance = "10"` |
| 409 | .../internal-route-distance = "100" | `BGP_DISTANCE_IPV4|bgp_ipv4|ibgpdistance = "100"`, `BGP_DISTANCE_IPV6|bgp_ipv6|ibgpdistance = "100"` |
| 410 | .../local-route-distance = "100" | `BGP_DISTANCE_IPV4|bgp_ipv4|localdistance = "100"`, `BGP_DISTANCE_IPV6|bgp_ipv6|localdistance = "100"` |
| 423 | peer-group Core/IPV4_UNICAST/apply-policy/config/export-policy = ["To-Core"]; Core-IPv6/IPV6_UNICAST/export = ["To-Core-IPv6"] | `BGP_NEIGHBOR_IPV4|Core|routemapout = ["To-Core"]`, `BGP_NEIGHBOR_IPV6|Core-IPv6|routemapout = ["To-Core-IPv6"]` |
| 424 | same peer-groups config/import-policy | `BGP_NEIGHBOR_IPV4|Core|routemapin = ["From-Core"]`, `BGP_NEIGHBOR_IPV6|Core-IPv6|routemapin = ["From-Core-IPv6"]` |
| 425 | Core/IPV4_UNICAST/afi-safi-name (presence; YV `default` -> "activate") | `BGP_NEIGHBOR_IPV4|Core|active = "activate"` |
| 426 | Core-IPv6/IPV6_UNICAST/afi-safi-name, 2 targets: v6 activate, v4 "no-activate" | `BGP_NEIGHBOR_IPV6|Core-IPv6|active = "activate"`, `BGP_NEIGHBOR_IPV4|Core-IPv6|active = "no-activate"` |
| 428 | peer-group {Core, Core-IPv6}/config/peer-group-name | `BGP_PEER_RANGE|Core|name = "Core"`, `BGP_PEER_RANGE|Core-IPv6|name = "Core-IPv6"` |
| 429 | peer-group .../config/auth-password = "hellotencent" | `BGP_PEER_RANGE|Core|password = "hellotencent"`, `BGP_PEER_RANGE|Core-IPv6|password = "hellotencent"` |
| 431 | peer-group .../config/peer-as = "103" | `BGP_PEER_RANGE|Core|remote_as = "103"`, `BGP_PEER_RANGE|Core-IPv6|remote_as = "103"` |

Notes:
* 394/395 `$VERSION1$` binds from `IPV4_UNICAST` -> 4; the IPv6 afi-safi has no
  advertise-routes subtree, so no `BGP_NETWORKS_IPV6` rows exist.
* 407-410 use a single `$VERSION$` placeholder (not `$VERSION1$`/`$VERSION2$`), so the
  SONiC key component is `bgp_ipv4` / `bgp_ipv6`.
* 401's enum `[['KERNEL','OSPF','OSPF6','default']]`->`[['kernel','ospf','ospf6','connected']]`
  is only exercised at index 0 ("KERNEL" -> "kernel"), which is robust under any
  reading of the enum selector.
* 426 is the only multi-target row in this group that fires. Its `sonic_value`
  `[[['activate']],[['no-activate']]]` has the supplier's extra per-target wrapper
  (same shape as ACL row 58 `[[[['SNMP']]]...`); after unwrapping one level the two
  candidates are single-string items -> JSON strings, not lists.

## 2. Suppressed rules (18) - matched a leaf but lost the literal-count precedence

All 18 are the generic `$NETWORK$` twin of a `global`-literal rule that wins.

| suppressed row | matched leaf | winner that suppresses it |
|---|---|---|
| 439 | peer-group Core & Core-IPv6 /config/peer-group-name | 428 |
| 440 | peer-group .../config/auth-password | 429 |
| 441 | peer-group .../config/peer-as | 431 |
| 442 | Core/IPV4_UNICAST/afi-safi-name | 425 |
| 443 | Core-IPv6/IPV6_UNICAST/afi-safi-name | 426 |
| 444 | Core & Core-IPv6 /apply-policy/config/export-policy | 423 |
| 445 | Core & Core-IPv6 /apply-policy/config/import-policy | 424 |
| 446 | bgp/global/config/as | 383 |
| 447 | bgp/global/config/router-id | 384 |
| 451 | bgp/global/advertise-delay/config/time | 388 |
| 466 | 4 IPv4 advertise-route /config/prefix leaves | 394 |
| 467 | 4 IPv4 advertise-route /config/policy leaves | 395 |
| 473 | 2 KERNEL /config/protocol leaves | 401 |
| 474 | 2 KERNEL /config/import-policy leaves | 402 |
| 479 | 2 maximum-paths leaves | 407 |
| 480 | 2 external-route-distance leaves | 408 |
| 481 | 2 internal-route-distance leaves | 409 |
| 482 | 2 local-route-distance leaves | 410 |

They must emit **nothing** (otherwise a duplicate `|<network>|`-prefixed key,
e.g. `BGP_NETWORKS_IPV4|global|22.215.246.64/26`, would appear next to the correct one).
See ambiguity A1.

## 3. Cannot match (206 rows)

### 3.1 multicast (15): rows 168,169,170,171,172,173,174,175,176,177,178,179,180,181,182
The OC document has **no root key `multicast`** (15 roots: stp, lldp, bfd,
YANG_VALIDATION, int, default, relay-agent, lacp, acl, network-instances, components,
qos, routing-policy, system, interfaces). `L2_MC_GROUP*`, `TRAFFIC_BEHAVIOR`,
`TRAFFIC_CLASSIFIER`, `POLICY` are therefore never created.

### 3.2 BGP global: leaves the document does not have (9): rows 385,386,387,389,390,391,392,393,411
`use-4byte-as`, `default-ipv4`, `keepalive-and-holdtime`, `startup-max-med/{time,max-med}`,
`route-selection-options/as-path-multipath-relax`, `graceful-restart/{enabled,restart-time}`,
`route-selection-options/always-compare-med`. The document only populates
`config/as`, `config/router-id`, `advertise-delay/config/time`, afi-safis, peer-groups.

### 3.3 BGP global afi-safi features the document does not have (9): rows 396,397,398,399,400,403,404,405,406
No `aggregate-routes` subtree (396-398); only `redistribute-route/KERNEL` exists, so
`redistribute-route/DIRECTLY_CONNECTED` (399-400), `/OSPF` (403-404), `/OSPF6` (405-406) never match.

### 3.4 BGP global neighbors (11): rows 412,413,414,415,416,417,418,419,420,421,422
The document has **no `bgp/neighbors` subtree at all** (both instances combined), so no
`BGP_NEIGHBOR` key is ever created from a neighbor leaf. (BGP_NEIGHBOR_* keys in the
expected file come only from the peer-group afi-safi rules 425/426.)

### 3.5 BGP global peer-group leaves the document does not have (8): rows 427,430,432,433,434,435,436,437
`next-hop-option/config/set-local`, `transport/config/local-interface`,
`enable-bfd/config/{enabled,detection-multiplier,required-minimum-receive,desired-minimum-tx-interval}`,
`config/addpath-tx-all-paths`, `route-reflector/config/route-reflector-client`.
The peer-groups only carry name/peer-as/auth-password/peer-type/send-community/
timers/minimum-advertisement-interval/afi-safis/apply-policy/default-route-distance.

### 3.6 `$NETWORK$` (and `underlay`) variants with no matching leaf (37):
rows 438,448,449,450,452,453,454,455,456,457,458,459,460,461,462,463,464,465,468,469,470,471,472,475,476,477,478,483,484,485,486,487,488,489,490,491,492
* 438 `$NETWORK$/config/create-hw-vrf`: no `create-hw-vrf` leaf under either instance
  (mgt_vrf only has name/type/route-distinguisher) -> **no `VRF` table entry is emitted
  for mgt_vrf at all** (see A4).
* 448-450,452-454,455-465,468-472,475-478,483-492: generic-VRF twins of the absent
  features above (IPv6 neighbours, DIRECTLY_CONNECTED/OSPF redistribute, aggregate
  routes, BFD, advertise-delay, network-import-check, prefix distance, etc.); no leaf.
* 460 is the only rule with literal instance `underlay`; the document has no `underlay`
  network-instance.

### 3.7 OSPF / OSPFv3 (104): rows 494-597
The document contains only two protocols: `BGP BGP` (global instance) and
`STATIC STATIC` (mgt_vrf). No `OSPF OSPF` protocol node exists, so every OSPFv2 rule
(494-545: `$NETWORK$` and `global` variants) and every OSPFv3 rule (546-597) is dead
here. This includes `OSPF_INTF`, `OSPF_ROUTER`, `OSPF6_INTF`, `OSPF6_ROUTER`.

### 3.8 prefix-limit / prefix-limit-v6 (12): rows 598,599,600,601,602,603,604,605,606,607,608,609
No `prefix-limit` or `prefix-limit-v6` leaf anywhere in the document.

### 3.9 STATIC route (1): row 493
`network-instances//network-instance//global//protocols//protocol//STATIC STATIC//static-routes/static/$IPADDR$/$IPMASK$//next-hops/next-hop/$HOP$//config/next-hop`
hard-codes the instance name `global`, but the document's **only** static route lives under
`network-instance/mgt_vrf/.../static-routes/static/0.0.0.0/0/next-hops/next-hop/1/...`
(next-hop "22.156.39.1", interface-ref eth0, description "Out-Of-Band-Management").
`global` has no `STATIC STATIC` protocol. So **`STATIC_ROUTES` is empty for this document**
(see A4). The row's DSL is also malformed/atypical (an `ockey` directive is embedded
inside the `sonic_key` as `$VALUE${|ockey=<path>}`, and its yang_value is
`[['ockey', <description path>], ['ocvalue']]`), so even if it matched its semantics are
unclear; it is not exercised here.

## 4. Ambiguities / open questions

**A1 (top, affects the whole group): instance name `global` vs the `$NETWORK$` fallback rows.**
`network-instances/network-instance/<name>/...` puts the instance name in the WILDCARD
position of `$NETWORK$` rules but in a LITERAL position of the 383-437 family. The document
has instance names `global` and `mgt_vrf`. If a `$NETWORK$` rule were allowed to bind
`global`, then every BGP global leaf would be emitted twice (e.g.
`BGP_GLOBALCONFIG|bgpGlobal|routeId` *and* `BGP_GLOBALCONFIG|global|bgpGlobal|routeId`;
`DEVICE_METADATA|localhost|bgp_asn` *and* `BGP_VRF|global|bgp_asn`; `BGP_NETWORKS_IPV4|<prefix>`
*and* `BGP_NETWORKS_IPV4|global|<prefix>`). The contract's "most literal segments wins"
rule avoids this and is the only self-consistent reading (the `global` family maps the
default instance to the legacy SONiC tables, the `$NETWORK$` family is for additional
VRFs). I followed it; 18 rows are therefore suppressed. If the Lead's engine instead lets
both fire, these 18 rows add ~40 spurious emissions - please diff specifically for this.

**A2: `unchanged` on a list-valued leaf (row 159, helper-address).**
The OC leaf is a JSON list of 5 helper addresses; `[['unchanged']]` has no `list_value`
directive. Contract 3.1 says "pass the OC leaf value through", so I emit the JSON array
`["28.231.67.5", ...]`. Alternative reading: join into one comma-separated string
(`"28.231.67.5,28.231.67.6,..."`), which is also a plausible SONiC `dhcp_servers` form.
If the engine differs here it is 1 line.

**A3: row 426 second target "no-activate".**
For a peer-group that has only IPV6_UNICAST, the rule emits
`BGP_NEIGHBOR_IPV6|<grp>|active = "activate"` **and**
`BGP_NEIGHBOR_IPV4|<grp>|active = "no-activate"`. Faithful to the CSV, but note the
asymmetry: a single-afi peer-group deliberately writes a negative value into the other
AFI table. Rule 425 (IPv4-only) has no such counterpart. Worth a glance in the final diff.

**A4: mgt_vrf is almost completely uncovered (biggest functional gap).**
For `network-instance/mgt_vrf` the document has `config/{name,type,route-distinguisher}`,
`interfaces/interface/eth0`, and the static default route. The CSV has NO rule for any of
these: no `config/type`/`route-distinguisher` mapping, no rule for
`network-instance/$NETWORK$/interfaces/interface`, and the only STATIC_ROUTES rule (493)
is hard-coded to the `global` instance. Consequences: no `VRF|mgt_vrf`, no static route
`0.0.0.0/0`, no mgt interface binding. This looks like a supplier-table gap (the management
VRF is often configured out-of-band), not a document quirk. Do **not** invent mappings;
flag as unsupported in the deliverable. (Also: mgt_vrf/`config/type = "L3VRF"` is the only
signal that could drive `VRF|mgt_vrf`, but no rule consumes it.)

**A5: enum selector when the leaf value is not in the yang_value list.**
Rows 399/403/405 map literal redistribute protocols (`DIRECTLY_CONNECTED`, `OSPF`,
`OSPF6`) but their yang_value lists are `['OSPF','OSPF6','default']` and do not contain the
literal protocol string. The contract gives no rule for an out-of-list value (candidate 0?
last? no-op?). Not exercised in this document (only KERNEL, cleanly index 0), but the Lead's
engine needs a defined fallback and it will show up on other samples.

**A6: `BGP_NETWORKS_IPV4` table naming.** The CSV emits `BGP_NETWORKS_IPV4`/
`BGP_REDISTRIBUTES_IPV4`/`BGP_DISTANCE_IPV4`/`BGP_CONFIG_IPV4` (all trailing the AFI).
If the expected answer uses a different (e.g. un-suffixed) table set this is a systematic
difference; the table is followed literally.

**A7: contract section 5 line format is ambiguous for empty-FIELD emissions.**
The example `LOOPBACK_INTERFACE|Loopback0|22.141.134.164/32 = {}` reads as
TABLE|KEY|FIELD but actually drops the empty FIELD slot, while a real key can itself
contain `|`. All 38 lines here have a non-empty FIELD, but if the Lead mechanically splits
on `|` to build the table map, the 2-segment/`{}` lines from other groups will mis-parse.
Recommend parsing by ` = ` first, then treating the FIELD as the JSON key after the last
`|` only when it is known to exist (or normalize via the engine's JSON).

**A8: relay-agent VLAN key naming.** Rule 158/159 translate OC interface key
`Vlan-interface2` to SONiC `Vlan2` (`$INTERFACEID$`=2). Note the OC document also has a
separate `interfaces/interface/Vlan2` object; the VLAN table's other fields
(description, vlanid, proxy flags, ...) come from the other audit group's
`interfaces//interface//Vlan$INTERFACEID$//...` rows 119-130, so the final VLAN|Vlan2
object is a union of two rule groups (no field conflict with my 2 lines).

**A9: table-level overlap with other groups.** My rows also touch
`DEVICE_METADATA|localhost|bgp_asn` (row 383). The `DEVICE_METADATA//localhost` spine rows
(e.g. row 722) have yang_keys that are already SONiC paths, so they never match this OC
document; row 383 is the only supplier for `bgp_asn` here. No conflict, just note that the
final `DEVICE_METADATA` object merges that line with the system-group rows.

## 5. Contract corrections / confirmations

* Section 1 "769 data rows / 15 root keys" - confirmed.
* Section 2.2 precedence "largest number of literal segments" - **required**; it is the
  only thing that makes the 383-437 vs 439-492 twin families behave (A1). No `NONE`
  row exists in my scope, so suppression-by-NONE is not exercised.
* Section 2.1 "one segment may hold several placeholders": confirmed for
  `IPV$VERSION1$_UNICAST`, `ipv$VERSION2$-unicast`, `$IPADDR$/$IPMASK$` (a whole
  `x.y.z.w/nn` dict key is one segment) and `Vlan-interface$INTERFACEID$`.
* Section 3.1 `['default']` = constant candidate 0 - confirmed (rows 425/426).
* Section 3.3 nesting: the CSV has an extra per-target wrapper on **multi-target** rows
  (`[[['activate']],[['no-activate']]]` vs `[['activate']]`); unwrap one level for
  multi-`sonic_key` rows before applying candidate semantics (see section 1 note).
* Section 5 field/`{}` ambiguity: see A7.
* Section 6.4 (VLAN name source) partially answered: the document's
  `network-instances/.../vlans/vlan/2/config/name = "PM&VM&TPC-Access"` has **no covering
  rule**; the `VLAN|Vlan2` object in the output is built entirely from the
  `interfaces` group (which sees `interfaces/interface/Vlan2/config/description =
  "PM&VM-Access"`). So `network-instances` `vlans` is dead weight in this document.

## 6. OC leaves in my scope with no covering rule (73 of 110)

relay-agent (6): `Vlan-interface2/{id, config/id, config/enable,
agent-information-option/config/enable, config/source-address}` and
`relay-agent/dhcp/config/enable-relay-agent` - no rule; `DHCP_RELAY`/`VLAN.source_address`
not emitted.

network-instances/global (49):
* `name`, `config/name`, `config/type` (instance identity; no rule) (3)
* `vlans/vlan/2/{vlan-id, config/vlan-id, config/name}` (3; see contract 6.4)
* protocol identity: `protocol/BGP BGP/{identifier, name,identifier, name,
  config/identifier, config/name}` (5)
* BGP global afi-safi: bare `afi-safi-name` and `config/afi-safi-name`, `config/enabled`
  for IPV4 and IPV6 (6); `use-multiple-paths/config/enabled` and
  `use-multiple-paths/ebgp/config/balance-as-path-relax` (4); bare
  `redistribute-route/KERNEL/protocol` (2); 4x advertise-route bare `prefix` and 4x
  `config/mode = "STATIC"` (8)
* peer-groups (Core, Core-IPv6): bare `peer-group-name` (2),
  `timers/config/minimum-advertisement-interval` (2), `config/peer-type` and
  `config/send-community` (4), afi-safi `config/afi-safi-name` + `config/enabled` (4),
  `default-route-distance/config/{external,local,internal}` (6)

network-instances/mgt_vrf (18):
* `name`, `config/name`, `config/type`, `config/route-distinguisher` (4)
* `interfaces/interface/eth0/{id, config/id}`
* static route: `static-routes/static/0.0.0.0/0/{prefix, config/prefix,
  config/description}`, `next-hop/1/{index, config/index, config/next-hop}`,
  `next-hop/1/interface-ref/config/interface`, `protocol/STATIC STATIC/{identifier,
  name,identifier, name, config/identifier, config/name}`

multicast: root absent, 0 leaves.
