# task-3 audit: `system//*`, `components//component`, `YANG_VALIDATION//config`, `telemetry-system//*`,
# uppercase-template spines (SYSTEM_PORT/BUFFER_*/DEVICE_METADATA/PBR_*/BGP_VRF*/LLDP_GLOBAL/NTP/SNMP/TACPLUS/SYSLOG_SERVER/TELEMETRY)

Scope: the 288 CSV data rows whose `spine` belongs to this audit (see per-spine inventory).
Inputs (read-only):
- rules: `references/raw/yang2sonic_maptable(1).csv`, sha256 `185821bee5fd1bf4d24ffd80bc531a96f37fd97eacb7f581cb7b6500e91054eb`
- OC doc: `data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt`, sha256 `0b5227b874caf7c38910dad32b6f4076a0ad341b8cf41079eda14164f59ddf76`
- expected file: `audit/system.expected.txt`, sha256 `1ae367c1deb52b6b83efbd85eb73040816b8877f6bf4e33488f71fa4b55258fa`

Result: **82 of 288 rules match at least one document leaf; the expected file has 738 final emission lines.**

## 0. Conventions used for `audit/system.expected.txt`

- One line per **final** `TABLE|KEY|FIELD = <json>`, sorted by the `TABLE|KEY|FIELD` string. Rule-row index and the concrete
  OC path that produced the final value follow as `  # row N; path`. Where the same field is written twice (duplicate rows or
  a later rule overwriting an earlier constant) only the final value is listed and the superseded emission is described here.
  This matches what the engine's JSON output can contain; if you prefer one line per raw emission, the extra lines are listed
  in the per-rule verdicts below.
- `empty_dict` targets (2-segment `sonic_key`) are written `TABLE|KEY = {}` (no field/`FIELD` part).
- `[TABLE|KEY]` candidates are foreign-key references: the emitted value is the referenced KEY name (see C2).
- Value DSL: `unchanged` copies the leaf; `default` is a constant branch 0; `true/false` and enumeration selectors index
  the candidate list by the leaf value; `ockey`+`ocvalue` substitutes the looked-up value; `list_combination`
  **accumulates into a JSON list** (see correction C1).

## 1. Corrections to `docs/ENGINE_CONTRACT.md` (please fold into the engine)

**C1 (must-fix). `list_combination` = accumulate a JSON list, not `"emit the raw string as one value"` (contract §3.2).**
Rows 348 and 254 fire on this document and only make sense as aggregations: `system//dns//servers//server//$SERVER$//address`
must yield `DNS|server|ip = ["9.128.49.48","9.128.49.49","9.54.85.132"]` and
`system//logging//...//remote-server//$SERVER$//config//host` must yield the 4-element list
`SYSLOG_SERVER|syslog_server|servers`. The same directive type is used by rows 418/461 for
`BGP_PEER_RANGE//<peer-group>//ip_range` (a list of neighbour IPs), which confirms the list-accumulation reading.
With the contract's literal reading the DNS rule keeps only the last address and the syslog rule only one server,
i.e. it loses 2/3 resp. 3/4 of the input. Implementation: append each substituted candidate to the target field's list in
(rule, document) order; a leaf whose value is itself a list contributes its elements (ACL_TABLE ports, row 61).
The `$VALUE_LIST$` expansion part of §3.2 remains correct (it is used only by interface/VLAN rows, not by this audit).

**C2. `[TABLE|KEY]` in `sonic_value` is *reference notation*: emit the referenced KEY, not the bracketed text (engine agrees).**
Rows 677/681 (this audit) use candidates such as `[BUFFER_PROFILE|egress_profile_+INTERFACE+_+QUEUEID+]` and
`[BUFFER_POOL|egress_lossy_pool]`. The referenced tables are produced by this same mapping table
(`BUFFER_PROFILE//egress_profile_$INTERFACE$_$QUEUEID$` from row 677 itself, `BUFFER_POOL//ingress_lossy_pool` from rows 674-676),
i.e. the bracket content is exactly `<target table>|<target key>`, and SONiC stores these references as the key *name*
(bare leafref in the SONiC schema): `BUFFER_QUEUE|Eth...|5|profile = "egress_profile_Eth..._5"`,
`BUFFER_PG|Eth...|5|profile = "ingress_profile_Eth..._5"`, `BUFFER_PROFILE|...|pool = "egress_lossy_pool"` /
`"ingress_lossy_pool"`. This audit uses that reading; the contract's literal-string reading of §3.3
(`"[BUFFER_PROFILE|egress_profile_...]"`) is rejected. The table uses the same notation for other reference fields
(rows 612-617: `dscp_to_tc_map`, `tc_to_queue_map`, `wred_profile`, `scheduler`, `ebst_profile`), so the same strip-to-key
rule applies there - but whether some of those fields keep the `TABLE|` qualification in the reference answer
(e.g. SONiC `PORT_QOS_MAP` map fields are often stored qualified) is outside this audit's rows.

**C3. Specificity tie on `$INTERFACE$` vs mixed literal segment (rows 188/194 and 189/195).** Contract §2.2 says
"largest number of literal (non-placeholder) segments". Counting only *fully literal* segments makes
`...//Bridge-Aggregation$INTERFACEID$//downlink//config//enable` (row 188) and
`...//$INTERFACE$//downlink//config//enable` (row 194) both 9 literal segments -> a tie, and rule 3 would emit **both**
`PORTCHANNEL|PortChannel13|...` and `PORT|Bridge-Aggregation13|...`. Counting segments that contain literal text, or
literal characters, makes the Bridge-Aggregation rows strictly more specific, which is clearly the supplier intent
(Bridge-Aggregation is a port-channel, not a PORT). I used the latter: rows 188/189 suppress 194/195 for the 16
Bridge-Aggregation interfaces. If the engine implements a strict fully-literal-segment count, add these 80 lines:
for each of Bridge-Aggregation1..16, `PORT|Bridge-AggregationN|updelaytime="120"`, `|linkmode="downlink"`,
`|groupid="1"`, `|option="add"` (from row 194) and `PORT|Bridge-AggregationN|threshold="0"` (from row 195).

**C4. `compute` formatting.** `log2(original)` on `"8"` -> `"3"`, on `"1/8"` -> `"-3"`; I emitted mathematically
integral results as integer strings (`"3"`, not `"3.0"`). Contract does not state this.

**C5. `lowercase` row 674**: both the selector and the candidate are the token `lowercase`; I treated it as
"lower-case the leaf value and emit it", giving `BUFFER_POOL|ingress_lossy_pool|mode = "dynamic"`.

**C6. Overwrite/duplicate rows (applied):** rows 206 and 207 are identical (`system/config/role` ->
`DEVICE_METADATA|localhost|type = "LA"`), rows 259/264 (`FLEX_COUNTER_TABLE|BUFFER_POOL|FLEX_COUNTER_STATUS`) and
278/283 (`...|POLL_INTERVAL`) are identical duplicates; row 202 fires once per TACACS server with the same passkey.
All are idempotent so the expected file has one line each.

**C7. `SYSLOG_SERVER|syslog_server|level` is written twice by two different rules** (row 254 constant `notice`, row 255
`INFO -> info`). Applying "later CSV order wins" gives `level = "info"`; `notice` never survives. This field is one
keyless aggregate for all 4 servers, which is suspicious (the table has no per-server SYSLOG_SERVER key) but faithful.

## 2. Per-spine inventory

| spine | rules | fire | final emission lines |
|---|---|---|---|
| `system//monitor-link` | 9 | 5 | 160 |
| `system//aaa` | 7 | 6 | 8 |
| `system//breakout` | 1 | 0 | 0 |
| `system//config` | 10 | 6 | 5 |
| `system//arp` | 1 | 1 | 1 |
| `system//nd` | 2 | 2 | 2 |
| `system//grpc` | 7 | 4 | 4 |
| `system//gnoi` | 1 | 0 | 0 |
| `system//hash` | 29 | 3 | 3 |
| `system//logging` | 2 | 2 | 2 |
| `system//ntp` | 1 | 1 | 1 |
| `system//snmp` | 2 | 1 | 2 |
| `system//counter` | 38 | 24 | 22 |
| `system//overlay` | 51 | 0 | 0 |
| `system//dns` | 1 | 1 | 1 |
| `system//mirrors` | 7 | 0 | 0 |
| `system//mod` | 3 | 0 | 0 |
| `system//fcr` | 5 | 0 | 0 |
| `system//sampling` | 9 | 9 | 102 |
| `telemetry-system//global` | 1 | 0 | 0 |
| `telemetry-system//destination-groups` | 1 | 0 | 0 |
| `telemetry-system//subscriptions` | 8 | 0 | 0 |
| `components//component` | 25 | 15 | 423 |
| `SYSTEM_PORT//SYSTEM_PORT_LIST` | 6 | 0 | 0 |
| `BUFFER_POOL//BUFFER_POOL_LIST` | 4 | 0 | 0 |
| `DEVICE_METADATA//localhost` | 21 | 0 | 0 |
| `YANG_VALIDATION//config` | 2 | 2 | 2 |
| `LLDP_GLOBAL//global` | 1 | 0 | 0 |
| `NTP//global` | 1 | 0 | 0 |
| `SNMP//snmp` | 1 | 0 | 0 |
| `TACPLUS//global` | 1 | 0 | 0 |
| `SYSLOG_SERVER//syslog_server` | 2 | 0 | 0 |
| `TELEMETRY//gnmi` | 1 | 0 | 0 |
| `BUFFER_PROFILE//BUFFER_PROFILE_LIST` | 7 | 0 | 0 |
| `BUFFER_QUEUE//BUFFER_QUEUE_LIST` | 1 | 0 | 0 |
| `BGP_VRF//BGP_VRF_LIST` | 4 | 0 | 0 |
| `BGP_VRF_LEAKING_IPV4//BGP_VRF_LEAKING_IPV4_LIST` | 1 | 0 | 0 |
| `BGP_VRF_LEAKING_IPV6//BGP_VRF_LEAKING_IPV6_LIST` | 1 | 0 | 0 |
| `PBR_NHG//PBR_NHG_LIST` | 1 | 0 | 0 |
| `PBR_NHG_MEMBER//PBR_NHG_MEMBER_INTF_LIST` | 1 | 0 | 0 |
| `PBR_NHG_MEMBER//PBR_NHG_MEMBER_LIST` | 1 | 0 | 0 |
| `PBR_RULE//PBR_RULE_LIST` | 9 | 0 | 0 |
| `BUFFER_PG//BUFFER_PG_LIST` | 1 | 0 | 0 |

Totals: 288 rules, 82 firing rows, 738 emission lines.

## 3. Rule-by-rule verdicts

`fire` = pattern matches >=1 document leaf. `emits` = final lines in `audit/system.expected.txt` attributed to that row.
A row can match but emit 0 lines either because it is *suppressed* by a more specific rule (C3) or because it is a
*duplicate* of a later identical row; both cases are called out explicitly per row.

### `system//monitor-link` - 9 rows, 5 firing, 160 lines

- R187: **NO-FIRE** - missing document key 'uplink' (pattern stops after `system/monitor-link/groups/group/$GROUP$/interfaces/interface/Bridge-Aggregation$INTERFACEID$`); `['PORTCHANNEL//PortChannel$INTERFACEID$//updelaytime', 'PORTCHANNEL//PortChannel$INTERFACEID$//linkmode', 'PORTCHANNEL//PortChannel$INTERFACEID$//groupid', 'PORTCHANNEL//PortChannel$INTERFACEID$//option']` is therefore never emitted.
- R188: fire (16 leaves, 64 lines); 64 lines, e.g. `PORTCHANNEL|PortChannel10|groupid = "1"`
- R189: fire (16 leaves, 16 lines); 16 lines, e.g. `PORTCHANNEL|PortChannel10|threshold = "0"`
- R190: **NO-FIRE** - no document key matches placeholder segment 'port-channel$INTERFACEID$' (pattern stops after `system/monitor-link/groups/group/$GROUP$/interfaces/interface`); `['PORTCHANNEL//PortChannel$INTERFACEID$//updelaytime', 'PORTCHANNEL//PortChannel$INTERFACEID$//linkmode', 'PORTCHANNEL//PortChannel$INTERFACEID$//groupid', 'PORTCHANNEL//PortChannel$INTERFACEID$//option']` is therefore never emitted.
- R191: **NO-FIRE** - no document key matches placeholder segment 'port-channel$INTERFACEID$' (pattern stops after `system/monitor-link/groups/group/$GROUP$/interfaces/interface`); `['PORTCHANNEL//PortChannel$INTERFACEID$//updelaytime', 'PORTCHANNEL//PortChannel$INTERFACEID$//linkmode', 'PORTCHANNEL//PortChannel$INTERFACEID$//groupid', 'PORTCHANNEL//PortChannel$INTERFACEID$//option']` is therefore never emitted.
- R192: **NO-FIRE** - no document key matches placeholder segment 'port-channel$INTERFACEID$' (pattern stops after `system/monitor-link/groups/group/$GROUP$/interfaces/interface`); `PORTCHANNEL//PortChannel$INTERFACEID$//threshold` is therefore never emitted.
- R193: fire (16 leaves, 64 lines); 64 lines, e.g. `PORT|Eth200GE17|groupid = "1"`
- R194: fire (16 leaves); **suppressed** - every matched leaf is claimed by a more specific rule (C3) -> 0 lines
- R195: fire (32 leaves, 16 lines); 16 lines, e.g. `PORT|Eth200GE17|threshold = "0"`
### `system//aaa` - 7 rows, 6 firing, 8 lines

- R196: fire (1 leaf, 1 line); AAA|account|commands = "tacacs+"
- R197: fire (1 leaf, 1 line); AAA|authorization|commands = "tacacs+"
- R198: fire (1 leaf, 1 line); AAA|authentication|login = "tacacs+,local"
- R199: **NO-FIRE** - missing document key 'config' (pattern stops after `system/aaa`); `AAA//authentication//failthrough` is therefore never emitted.
- R200: fire (2 leaves, 2 lines); TACPLUS_SERVER|10.12.220.198|tcp_port = "49"; TACPLUS_SERVER|172.16.0.196|tcp_port = "49"
- R201: fire (2 leaves, 2 lines); TACPLUS_SERVER|10.12.220.198|priority = "60"; TACPLUS_SERVER|172.16.0.196|priority = "50"
- R202: fire (2 leaves, 1 line); TACPLUS|global|passkey = "tcnw"
### `system//breakout` - 1 rows, 0 firing, 0 lines

- R203: **NO-FIRE** - missing document key 'breakout' (pattern stops after `system`); `BREAKOUT_CFG//$INTERFACE$//brkout_mode` is therefore never emitted.
### `system//config` - 10 rows, 6 firing, 5 lines

- R204: fire (1 leaf, 1 line); DEVICE_METADATA|localhost|hostname = "CQ-JLDC-2203-D05-TCS84R-LA200G-019"
- R205: fire (1 leaf, 1 line); DEVICE_METADATA|localhost|hwsku = "TCS8400-24CC8CD"
- R206: fire (1 leaf); **duplicate** of R207 (byte-identical yang_key/yang_value/sonic_key/sonic_value); the single line for the pair is attributed to R207 -> 0 lines
- R207: fire (1 leaf, 1 line); DEVICE_METADATA|localhost|type = "LA" (identical duplicate row(s) R206 collapse into this line)
- R208: **NO-FIRE** - missing document key 'asic-variant' (pattern stops after `system/config`); `DEVICE_METADATA//localhost//asic_variant` is therefore never emitted.
- R209: **NO-FIRE** - missing document key 'asic' (pattern stops after `system/config`); `DEVICE_METADATA//localhost//asic` is therefore never emitted.
- R210: fire (1 leaf, 1 line); SHELL|passwd|passwd = "10CENT.com"
- R211: fire (1 leaf, 1 line); ZTP|flg|run = "ok"
- R212: **NO-FIRE** - missing document key 'database-version' (pattern stops after `system/config`); `VERSIONS//DATABASE//VERSION` is therefore never emitted.
- R213: **NO-FIRE** - missing document key 'login-timeout' (pattern stops after `system/config`); `USER//timeout//value` is therefore never emitted.
### `system//arp` - 1 rows, 1 firing, 1 lines

- R214: fire (1 leaf, 1 line); DEVICE_METADATA|localhost|arp_to_route = "true"
### `system//nd` - 2 rows, 2 firing, 2 lines

- R215: fire (1 leaf, 1 line); DEVICE_METADATA|localhost|nd_to_route = "true"
- R216: fire (1 leaf, 1 line); DEVICE_METADATA|localhost|ndmask_v6 = "64"
### `system//grpc` - 7 rows, 4 firing, 4 lines

- R217: fire (1 leaf, 1 line); TELEMETRY|gnmi|status = "enable"
- R218: **NO-FIRE** - missing document key 'gnmi-direction' (pattern stops after `system/grpc/config`); `TELEMETRY//gnmi//gnmi_direction` is therefore never emitted.
- R219: **NO-FIRE** - missing document key 'port' (pattern stops after `system/grpc/config`); `TELEMETRY//gnmi//port` is therefore never emitted.
- R220: fire (1 leaf, 1 line); TELEMETRY|usrpwd|password = "10DOLLAR.com"
- R221: fire (1 leaf, 1 line); TELEMETRY|serverTls|type = "without-ca"
- R222: fire (1 leaf, 1 line); TELEMETRY|usrpwd|username = "tencent"
- R223: **NO-FIRE** - missing document key 'channel' (pattern stops after `system/grpc/config`); `TELEMETRY//channel//client` is therefore never emitted.
### `system//gnoi` - 1 rows, 0 firing, 0 lines

- R224: **NO-FIRE** - missing document key 'gnoi' (pattern stops after `system`); `TELEMETRY//gnoi//status` is therefore never emitted.
### `system//hash` - 29 rows, 3 firing, 3 lines

- R225: fire (1 leaf, 1 line); SWITCH|switch|ecmp_hash_alg = "9"
- R226: **NO-FIRE** - missing document key 'algorithm-lag' (pattern stops after `system/hash/global/config`); `SWITCH//switch//lag_hash_alg` is therefore never emitted.
- R227: fire (1 leaf, 1 line); SWITCH|switch|ecmp_hash_seed = "20"
- R228: fire (1 leaf, 1 line); SWITCH|switch|lag_hash_seed = "20"
- R229: **NO-FIRE** - missing document key 'lag-tunnel-hash' (pattern stops after `system/hash/global/config`); `SWITCH//switch//lag_tunnel_hash` is therefore never emitted.
- R230: **NO-FIRE** - missing document key 'ecmp-tunnel-hash' (pattern stops after `system/hash/global/config`); `SWITCH//switch//ecmp_tunnel_hash` is therefore never emitted.
- R231: **NO-FIRE** - missing document key 'ecmp-ipv4-hash-mode' (pattern stops after `system/hash/global/config`); `SWITCH//switch//ecmp_ipv4_hash_mode` is therefore never emitted.
- R232: **NO-FIRE** - missing document key 'ecmp-ipv6-hash-mode' (pattern stops after `system/hash/global/config`); `SWITCH//switch//ecmp_ipv6_hash_mode` is therefore never emitted.
- R233: **NO-FIRE** - missing document key 'lag-ipv4-hash-mode' (pattern stops after `system/hash/global/config`); `SWITCH//switch//lag_ipv4_hash_mode` is therefore never emitted.
- R234: **NO-FIRE** - missing document key 'lag-ipv6-hash-mode' (pattern stops after `system/hash/global/config`); `SWITCH//switch//lag_ipv6_hash_mode` is therefore never emitted.
- R235: **NO-FIRE** - missing document key 'hash-offset' (pattern stops after `system/hash/global/config`); `SWITCH//switch//hash_offset` is therefore never emitted.
- R236: **NO-FIRE** - missing document key 'dlb' (pattern stops after `system/hash`); `DLB_TABLE//global//cap_load` is therefore never emitted.
- R237: **NO-FIRE** - missing document key 'dlb' (pattern stops after `system/hash`); `DLB_TABLE//global//cap_queue` is therefore never emitted.
- R238: **NO-FIRE** - missing document key 'dlb' (pattern stops after `system/hash`); `DLB_TABLE//global//load_weight` is therefore never emitted.
- R239: **NO-FIRE** - missing document key 'dlb' (pattern stops after `system/hash`); `DLB_TABLE//global//queue_weight` is therefore never emitted.
- R240: **NO-FIRE** - missing document key 'dlb' (pattern stops after `system/hash`); `DLB_TABLE//global//load_min` is therefore never emitted.
- R241: **NO-FIRE** - missing document key 'dlb' (pattern stops after `system/hash`); `DLB_TABLE//global//load_max` is therefore never emitted.
- R242: **NO-FIRE** - missing document key 'dlb' (pattern stops after `system/hash`); `DLB_TABLE//global//queue_min` is therefore never emitted.
- R243: **NO-FIRE** - missing document key 'dlb' (pattern stops after `system/hash`); `DLB_TABLE//global//queue_max` is therefore never emitted.
- R244: **NO-FIRE** - missing document key 'dlb' (pattern stops after `system/hash`); `DLB_TABLE//global//dlb_sample_rate` is therefore never emitted.
- R245: **NO-FIRE** - missing document key 'dlb' (pattern stops after `system/hash`); `DLB_TABLE//global//dlb_ecmp_enable` is therefore never emitted.
- R246: **NO-FIRE** - missing document key 'dlb' (pattern stops after `system/hash`); `DLB_TABLE//global//dlb_hash_seed` is therefore never emitted.
- R247: **NO-FIRE** - missing document key 'dlb' (pattern stops after `system/hash`); `DLB_TABLE//$INTERFACE$//load_weight` is therefore never emitted.
- R248: **NO-FIRE** - missing document key 'dlb' (pattern stops after `system/hash`); `DLB_TABLE//$INTERFACE$//queue_size_weight` is therefore never emitted.
- R249: **NO-FIRE** - missing document key 'dlb' (pattern stops after `system/hash`); `DLB_TABLE//$INTERFACE$//scaling_factor` is therefore never emitted.
- R250: **NO-FIRE** - missing document key 'dhash' (pattern stops after `system/hash`); `FG_NHG//$GROUP$//fg_nhg_mode` is therefore never emitted.
- R251: **NO-FIRE** - missing document key 'dhash' (pattern stops after `system/hash`); `FG_NHG//$GROUP$//dynamic_age` is therefore never emitted.
- R252: **NO-FIRE** - missing document key 'dhash' (pattern stops after `system/hash`); `FG_NHG//$GROUP$//dynamic_mode` is therefore never emitted.
- R253: **NO-FIRE** - missing document key 'dhash' (pattern stops after `system/hash`); `FG_NHG//$GROUP$//dynamic_size` is therefore never emitted.
### `system//logging` - 2 rows, 2 firing, 2 lines

- R254: fire (4 leaves, 1 line); SYSLOG_SERVER|syslog_server|servers = ["22.144.124.133", "22.144.126.133", "22.144.125.133", "172.16.0.203"] (R254's `level="notice"` is then overwritten by R255 -> final `level="info"`; R254 only contributes the servers list)
- R255: fire (4 leaves, 1 line); SYSLOG_SERVER|syslog_server|level = "info"
### `system//ntp` - 1 rows, 1 firing, 1 lines

- R256: fire (1 leaf, 1 line); NTP_SERVER|172.16.0.203 = {}
### `system//snmp` - 2 rows, 1 firing, 2 lines

- R257: fire (1 leaf, 2 lines); SNMP|snmp|snmp_location = "public"; SNMP|snmp|snmp_rocommunity = "tcnw"
- R258: **NO-FIRE** - missing document key 'port' (pattern stops after `system/snmp/servers/server/$SERVER$/config`); `SNMP_AGENT_ADDRESS_CONFIG//$SERVER$|$VALUE$|mgmt` is therefore never emitted.
### `system//counter` - 38 rows, 24 firing, 22 lines

- R259: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|BUFFER_POOL|FLEX_COUNTER_STATUS = "enable" (identical duplicate row(s) R264 collapse into this line)
- R260: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|BUFFER_POOL_WATERMARK|FLEX_COUNTER_STATUS = "enable"
- R261: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|PG|FLEX_COUNTER_STATUS = "enable"
- R262: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|QUEUE_WATERMARK|FLEX_COUNTER_STATUS = "enable"
- R263: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|PG_WATERMARK|FLEX_COUNTER_STATUS = "enable"
- R264: fire (1 leaf); **duplicate** of R259 (byte-identical yang_key/yang_value/sonic_key/sonic_value); the single line for the pair is attributed to R259 -> 0 lines
- R265: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|PFCWD|FLEX_COUNTER_STATUS = "enable"
- R266: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|QUEUE|FLEX_COUNTER_STATUS = "enable"
- R267: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|PORT|FLEX_COUNTER_STATUS = "enable"
- R268: **NO-FIRE** - missing document key 'port-buffer-drop' (pattern stops after `system/counter`); `FLEX_COUNTER_TABLE//PORT_BUFFER_DROP//FLEX_COUNTER_STATUS` is therefore never emitted.
- R269: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|PORT_PHY|FLEX_COUNTER_STATUS = "enable"
- R270: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|ACL|FLEX_COUNTER_STATUS = "enable"
- R271: **NO-FIRE** - missing document key 'rif' (pattern stops after `system/counter`); `FLEX_COUNTER_TABLE//RIF//FLEX_COUNTER_STATUS` is therefore never emitted.
- R272: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|POLICER|FLEX_COUNTER_STATUS = "enable"
- R273: **NO-FIRE** - missing document key 'policer-stat' (pattern stops after `system/counter`); `FLEX_COUNTER_TABLE//POLICER_STAT_COUNTER//FLEX_COUNTER_STATUS` is therefore never emitted.
- R274: **NO-FIRE** - missing document key 'bridge' (pattern stops after `system/counter`); `FLEX_COUNTER_TABLE//BRIDGE_STAT_COUNTER//FLEX_COUNTER_STATUS` is therefore never emitted.
- R275: **NO-FIRE** - missing document key 'tunnel' (pattern stops after `system/counter`); `FLEX_COUNTER_TABLE//TUNNEL//FLEX_COUNTER_STATUS` is therefore never emitted.
- R276: **NO-FIRE** - missing document key 'debug' (pattern stops after `system/counter`); `FLEX_COUNTER_TABLE//DEBUG//FLEX_COUNTER_STATUS` is therefore never emitted.
- R277: **NO-FIRE** - missing document key 'ebst' (pattern stops after `system/counter`); `FLEX_COUNTER_TABLE//QUEUE_EBST//FLEX_COUNTER_STATUS` is therefore never emitted.
- R278: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|BUFFER_POOL|POLL_INTERVAL = "1000" (identical duplicate row(s) R283 collapse into this line)
- R279: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|BUFFER_POOL_WATERMARK|POLL_INTERVAL = "1000"
- R280: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|PG|POLL_INTERVAL = "1000"
- R281: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|QUEUE_WATERMARK|POLL_INTERVAL = "1000"
- R282: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|PG_WATERMARK|POLL_INTERVAL = "1000"
- R283: fire (1 leaf); **duplicate** of R278 (byte-identical yang_key/yang_value/sonic_key/sonic_value); the single line for the pair is attributed to R278 -> 0 lines
- R284: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|PFCWD|POLL_INTERVAL = "1000"
- R285: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|PORT|POLL_INTERVAL = "1000"
- R286: **NO-FIRE** - missing document key 'port-buffer-drop' (pattern stops after `system/counter`); `FLEX_COUNTER_TABLE//PORT_BUFFER_DROP//POLL_INTERVAL` is therefore never emitted.
- R287: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|PORT_PHY|POLL_INTERVAL = "20000"
- R288: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|ACL|POLL_INTERVAL = "1000"
- R289: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|QUEUE|POLL_INTERVAL = "1000"
- R290: **NO-FIRE** - missing document key 'rif' (pattern stops after `system/counter`); `FLEX_COUNTER_TABLE//RIF//POLL_INTERVAL` is therefore never emitted.
- R291: fire (1 leaf, 1 line); FLEX_COUNTER_TABLE|POLICER|POLL_INTERVAL = "1000"
- R292: **NO-FIRE** - missing document key 'policer-stat' (pattern stops after `system/counter`); `FLEX_COUNTER_TABLE//POLICER_STAT_COUNTER//POLL_INTERVAL` is therefore never emitted.
- R293: **NO-FIRE** - missing document key 'bridge' (pattern stops after `system/counter`); `FLEX_COUNTER_TABLE//BRIDGE_STAT_COUNTER//POLL_INTERVAL` is therefore never emitted.
- R294: **NO-FIRE** - missing document key 'tunnel' (pattern stops after `system/counter`); `FLEX_COUNTER_TABLE//TUNNEL//POLL_INTERVAL` is therefore never emitted.
- R295: **NO-FIRE** - missing document key 'debug' (pattern stops after `system/counter`); `FLEX_COUNTER_TABLE//DEBUG//POLL_INTERVAL` is therefore never emitted.
- R296: **NO-FIRE** - missing document key 'ebst' (pattern stops after `system/counter`); `FLEX_COUNTER_TABLE//QUEUE_EBST//POLL_INTERVAL` is therefore never emitted.
### `system//overlay` - 51 rows, 0 firing, 0 lines

- R297: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//global//enable` is therefore never emitted.
- R298: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//global//role` is therefore never emitted.
- R299: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//agent//listen_ip` is therefore never emitted.
- R300: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//agent//listen_port` is therefore never emitted.
- R301: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//agent//mgmt_ip` is therefore never emitted.
- R302: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//agent//usrname` is therefore never emitted.
- R303: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//agent//password` is therefore never emitted.
- R304: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//agent//vtep_if` is therefore never emitted.
- R305: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//agent//vtep_ip` is therefore never emitted.
- R306: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//agent//stat_interval` is therefore never emitted.
- R307: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//agent//config_restore` is therefore never emitted.
- R308: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//fcr//fcr_enable` is therefore never emitted.
- R309: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//fcr//fcr_listen_ip` is therefore never emitted.
- R310: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//fcr//fcr_listen_port` is therefore never emitted.
- R311: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//fcr//fcr_usrname` is therefore never emitted.
- R312: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//fcr//fcr_password` is therefore never emitted.
- R313: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//fcr//default_only` is therefore never emitted.
- R314: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//sync//acl_entries_max` is therefore never emitted.
- R315: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//sync//overlay_ecmp_max` is therefore never emitted.
- R316: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//sync//ipv4_route_entries_max` is therefore never emitted.
- R317: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//sync//ipv6_route_entries_max` is therefore never emitted.
- R318: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//sync//vxlan_l3_mac` is therefore never emitted.
- R319: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//sync//vxlan_nh_mac` is therefore never emitted.
- R320: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//sync//thrift_rpc_listen_ip` is therefore never emitted.
- R321: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//sync//thrift_rpc_listen_port` is therefore never emitted.
- R322: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//sync//vxlan_tunnel_entries_max` is therefore never emitted.
- R323: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//sync//siso_filter` is therefore never emitted.
- R324: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//resource_spec//ecmp_group` is therefore never emitted.
- R325: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//resource_spec//vrf` is therefore never emitted.
- R326: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//resource_spec//vxlan_tunnel` is therefore never emitted.
- R327: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//resource_spec//vxlan_vni` is therefore never emitted.
- R328: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//resource_spec//ipv4_route_prefix` is therefore never emitted.
- R329: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//resource_spec//overlay_acl` is therefore never emitted.
- R330: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//resource_spec//overlay_arp` is therefore never emitted.
- R331: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY//resource_spec//overlay_multicast` is therefore never emitted.
- R332: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_SAMPLER//$SAMPLER$//SAMPLE_RATE` is therefore never emitted.
- R333: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_SAMPLER//$SAMPLER$//DESTINATION` is therefore never emitted.
- R334: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_ACL_RULE//$RULE$//IN_PORT` is therefore never emitted.
- R335: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_ACL_RULE//$RULE$//DST_IP` is therefore never emitted.
- R336: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_ACL_RULE//$RULE$//PRIORITY` is therefore never emitted.
- R337: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_ACL_RULE//$RULE$//SAMPLE_ACTION` is therefore never emitted.
- R338: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_ACL_RULE//$RULE$//TRUNCATE_ACTION` is therefore never emitted.
- R339: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_ACL_RULE//$RULE$//TUNNEL_TERM` is therefore never emitted.
- R340: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_ACL_RULE//$RULE$//PACKET_ACTION_REDIRECT_GROUPID` is therefore never emitted.
- R341: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_ACL_RULE//$RULE$//VLAN_INNER_TAG_ACTION` is therefore never emitted.
- R342: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_ACL_RULE//$RULE$//VLAN_OUTER_TAG_ACTION` is therefore never emitted.
- R343: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_ACL_RULE//$RULE$//PACKET_ACTION` is therefore never emitted.
- R344: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_ACL_RULE//$RULE$//TRUNCATE_MIRROR_LENGTH` is therefore never emitted.
- R345: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_PORT//$INTERFACE$//sample_enable` is therefore never emitted.
- R346: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_TUNNEL//dscp//mode` is therefore never emitted.
- R347: **NO-FIRE** - missing document key 'overlay' (pattern stops after `system`); `OVERLAY_TUNNEL//dscp//value` is therefore never emitted.
### `system//dns` - 1 rows, 1 firing, 1 lines

- R348: fire (3 leaves, 1 line); DNS|server|ip = ["9.128.49.48", "9.128.49.49", "9.54.85.132"]
### `system//mirrors` - 7 rows, 0 firing, 0 lines

- R349: **NO-FIRE** - missing document key 'mirrors' (pattern stops after `system`); `MIRROR_SESSION//$MIRROR$//dst_ip` is therefore never emitted.
- R350: **NO-FIRE** - missing document key 'mirrors' (pattern stops after `system`); `MIRROR_SESSION//$MIRROR$//src_ip` is therefore never emitted.
- R351: **NO-FIRE** - missing document key 'mirrors' (pattern stops after `system`); `MIRROR_SESSION//$MIRROR$//dscp` is therefore never emitted.
- R352: **NO-FIRE** - missing document key 'mirrors' (pattern stops after `system`); `MIRROR_SESSION//$MIRROR$//udp_dst_port` is therefore never emitted.
- R353: **NO-FIRE** - missing document key 'mirrors' (pattern stops after `system`); `MIRROR_SESSION//$MIRROR$//udp_src_port` is therefore never emitted.
- R354: **NO-FIRE** - missing document key 'mirrors' (pattern stops after `system`); `MIRROR_SESSION//$MIRROR$//type` is therefore never emitted.
- R355: **NO-FIRE** - missing document key 'mirrors' (pattern stops after `system`); `MIRROR_SESSION//$MIRROR$//ttl` is therefore never emitted.
### `system//mod` - 3 rows, 0 firing, 0 lines

- R356: **NO-FIRE** - missing document key 'mod' (pattern stops after `system`); `MOD_MIRROR//L3_MISS//mirror_session` is therefore never emitted.
- R357: **NO-FIRE** - missing document key 'mod' (pattern stops after `system`); `MOD_MIRROR//L3_NEXT_HOP//mirror_session` is therefore never emitted.
- R358: **NO-FIRE** - missing document key 'mod' (pattern stops after `system`); `MOD_MIRROR//BUFFER//mirror_session` is therefore never emitted.
### `system//fcr` - 5 rows, 0 firing, 0 lines

- R359: **NO-FIRE** - missing document key 'fcr' (pattern stops after `system`); `FCR_GLOBALCONFIG//bgp_global//ipv6_nexthop_prefer_global` is therefore never emitted.
- R360: **NO-FIRE** - missing document key 'fcr' (pattern stops after `system`); `FCR_GLOBALCONFIG//bgp_global|network_delay//mode` is therefore never emitted.
- R361: **NO-FIRE** - missing document key 'fcr' (pattern stops after `system`); `FCR_GLOBALCONFIG//bgp_global|network_delay//delay_time` is therefore never emitted.
- R362: **NO-FIRE** - missing document key 'fcr' (pattern stops after `system`); `FCR_GLOBALCONFIG//ip_protocol|bgp//route_map` is therefore never emitted.
- R363: **NO-FIRE** - missing document key 'fcr' (pattern stops after `system`); `FCR_GLOBALCONFIG//grpc_control_interface//interface` is therefore never emitted.
### `system//sampling` - 9 rows, 9 firing, 102 lines

- R364: fire (32 leaves, 32 lines); 32 lines, e.g. `SFLOW_SESSION|Eth200GE10|sample_rate = "262144"`
- R365: fire (32 leaves, 32 lines); 32 lines, e.g. `SFLOW_SESSION|Eth200GE10|admin_state = "up"`
- R366: fire (32 leaves, 32 lines); 32 lines, e.g. `SFLOW_SESSION|Eth200GE10|sample_stage = "inbound"`
- R367: fire (1 leaf, 1 line); SFLOW|global|agent_id = "Loopback0"
- R368: fire (1 leaf, 1 line); SFLOW|global|admin_state = "up"
- R369: fire (1 leaf, 1 line); SFLOW|global|max_datagram_size = "1000"
- R370: fire (1 leaf, 1 line); SFLOW|global|cpu_rate_limit = "10000"
- R371: fire (1 leaf, 1 line); SFLOW_COLLECTOR|1|collector_ip = "30.46.231.93"
- R372: fire (1 leaf, 1 line); SFLOW_COLLECTOR|1|collector_port = "12339"
### `telemetry-system//global` - 1 rows, 0 firing, 0 lines

- R373: **NO-FIRE (dead spine group)** - rooted at `telemetry-system`, which is not an OC root of this document, so no document data can supply this rule; `TELEMETRY_CLIENT//Global//src_ip` is never emitted.
### `telemetry-system//destination-groups` - 1 rows, 0 firing, 0 lines

- R374: **NO-FIRE (dead spine group)** - rooted at `telemetry-system`, which is not an OC root of this document, so no document data can supply this rule; `TELEMETRY_CLIENT//DestinationGroup_$GROUP$//dst_addr` is never emitted.
### `telemetry-system//subscriptions` - 8 rows, 0 firing, 0 lines

- R375: **NO-FIRE (dead spine group)** - rooted at `telemetry-system`, which is not an OC root of this document, so no document data can supply this rule; `TELEMETRY_CLIENT//Subscription_$NAME$//dst_group` is never emitted.
- R376: **NO-FIRE (dead spine group)** - rooted at `telemetry-system`, which is not an OC root of this document, so no document data can supply this rule; `TELEMETRY_CLIENT//Subscription_$NAME$//band_direction` is never emitted.
- R377: **NO-FIRE (dead spine group)** - rooted at `telemetry-system`, which is not an OC root of this document, so no document data can supply this rule; `TELEMETRY_CLIENT//Subscription_$NAME$//report_interval` is never emitted.
- R378: **NO-FIRE (dead spine group)** - rooted at `telemetry-system`, which is not an OC root of this document, so no document data can supply this rule; `TELEMETRY_CLIENT//Subscription_$NAME$//path_target` is never emitted.
- R379: **NO-FIRE (dead spine group)** - rooted at `telemetry-system`, which is not an OC root of this document, so no document data can supply this rule; `TELEMETRY_CLIENT//Subscription_$NAME$//report_type` is never emitted.
- R380: **NO-FIRE (dead spine group)** - rooted at `telemetry-system`, which is not an OC root of this document, so no document data can supply this rule; `TELEMETRY_CLIENT//Subscription_$NAME$//value_type` is never emitted.
- R381: **NO-FIRE (dead spine group)** - rooted at `telemetry-system`, which is not an OC root of this document, so no document data can supply this rule; `TELEMETRY_CLIENT//Subscription_$NAME$//extend_type` is never emitted.
- R382: **NO-FIRE (dead spine group)** - rooted at `telemetry-system`, which is not an OC root of this document, so no document data can supply this rule; `TELEMETRY_CLIENT//Subscription_$NAME$//paths` is never emitted.
### `components//component` - 25 rows, 15 firing, 423 lines

- R673: fire (1 leaf, 1 line); BUFFER_NOTIFICATION|BUFFER_POOL|pool_share_th = "100000"
- R674: fire (1 leaf, 1 line); BUFFER_POOL|ingress_lossy_pool|mode = "dynamic"
- R675: fire (1 leaf, 2 lines); BUFFER_POOL|ingress_lossy_pool|size = "46110000"; BUFFER_POOL|ingress_lossy_pool|type = "ingress"
- R676: fire (1 leaf, 1 line); BUFFER_POOL|ingress_lossy_pool|xoff = "31800000"
- R677: fire (32 leaves, 96 lines); 96 lines, e.g. `BUFFER_PROFILE|egress_profile_Eth200GE10_5|dynamic_th = "3"`
- R678: fire (32 leaves, 32 lines); 32 lines, e.g. `BUFFER_PROFILE|egress_profile_Eth200GE10_5|size = "3180"`
- R679: fire (32 leaves, 32 lines); 32 lines, e.g. `BUFFER_NOTIFICATION|Eth200GE10|5|queue_share_th = "100000"`
- R680: **NO-FIRE** - missing document key 'profile' (pattern stops after `components/component/$COMPONENT$/integrated-circuit/chip/buffers/buffer/SHARED_BUFFER/interfaces/interface/$INTERFACE$/input/queues/queue/queue$QUEUEID$/config`); `BUFFER_PG//$INTERFACE$|$QUEUEID$//profile'` is therefore never emitted.
- R681: fire (32 leaves, 96 lines); 96 lines, e.g. `BUFFER_PG|Eth200GE10|5|profile = "ingress_profile_Eth200GE10_5"`
- R682: fire (32 leaves, 32 lines); 32 lines, e.g. `BUFFER_PROFILE|ingress_profile_Eth200GE10_5|xon_offset = "2544"`
- R683: fire (32 leaves, 32 lines); 32 lines, e.g. `BUFFER_PROFILE|ingress_profile_Eth200GE10_5|size = "0"`
- R684: fire (32 leaves, 32 lines); 32 lines, e.g. `BUFFER_NOTIFICATION|Eth200GE10|5|pg_shared_th = "7000"`
- R685: fire (32 leaves, 32 lines); 32 lines, e.g. `BUFFER_PROFILE|ingress_profile_Eth200GE10_5|xoff = "6360000"`
- R686: fire (32 leaves, 32 lines); 32 lines, e.g. `BUFFER_NOTIFICATION|Eth200GE10|5|pg_hdrm_th = "12000"`
- R687: **NO-FIRE** - missing document key 'hbm' (pattern stops after `components/component/$COMPONENT$/integrated-circuit/chip/buffers/buffer/SHARED_BUFFER/slices/slice`); `BUFFER_POOL//hbm//size` is therefore never emitted.
- R688: **NO-FIRE** - missing document key 'hbm' (pattern stops after `components/component/$COMPONENT$/integrated-circuit/chip/buffers/buffer/SHARED_BUFFER/slices/slice`); `BUFFER_POOL//hbm//type` is therefore never emitted.
- R689: **NO-FIRE** - missing document key 'sms' (pattern stops after `components/component/$COMPONENT$/integrated-circuit/chip/buffers/buffer/SHARED_BUFFER/slices/slice`); `BUFFER_POOL//sms//size` is therefore never emitted.
- R690: **NO-FIRE** - missing document key 'sms' (pattern stops after `components/component/$COMPONENT$/integrated-circuit/chip/buffers/buffer/SHARED_BUFFER/slices/slice`); `BUFFER_POOL//sms//type` is therefore never emitted.
- R691: fire (1 leaf, 1 line); BUFFER_NOTIFICATION|Suppress|time = "30"
- R692: fire (1 leaf, 1 line); BUFFER_NOTIFICATION|Suppress|number = "5"
- R693: **NO-FIRE** - missing document key 'dwdm' (pattern stops after `components/component/$COMPONENT$`); `DWDM_PORT_INFO//$INTERFACE$//admin_status` is therefore never emitted.
- R694: **NO-FIRE** - missing document key 'dwdm' (pattern stops after `components/component/$COMPONENT$`); `DWDM_TRANSCEIVER_INFO//TRANSCEIVER-$INTERFACE$|0//tx-laser` is therefore never emitted.
- R695: **NO-FIRE** - missing document key 'dwdm' (pattern stops after `components/component/$COMPONENT$`); `DWDM_OPTICAL_CHANNEL_INFO//OCH-$INTERFACE$//frequency` is therefore never emitted.
- R696: **NO-FIRE** - missing document key 'dwdm' (pattern stops after `components/component/$COMPONENT$`); `DWDM_OPTICAL_CHANNEL_INFO//OCH-$INTERFACE$//target-output-power` is therefore never emitted.
- R697: **NO-FIRE** - missing document key 'dwdm' (pattern stops after `components/component/$COMPONENT$`); `DWDM_OPTICAL_CHANNEL_INFO//OCH-$INTERFACE$//operational-mode` is therefore never emitted.
### `SYSTEM_PORT//SYSTEM_PORT_LIST` - 6 rows, 0 firing, 0 lines

- R702: **NO-FIRE (dead spine group)** - rooted at `SYSTEM_PORT`, which is not an OC root of this document, so no document data can supply this rule; `SYSTEM_PORT//$NAME$|$ASIC$|$PORT$//core_index` is never emitted.
- R703: **NO-FIRE (dead spine group)** - rooted at `SYSTEM_PORT`, which is not an OC root of this document, so no document data can supply this rule; `SYSTEM_PORT//$NAME$|$ASIC$|$PORT$//core_port_index` is never emitted.
- R704: **NO-FIRE (dead spine group)** - rooted at `SYSTEM_PORT`, which is not an OC root of this document, so no document data can supply this rule; `SYSTEM_PORT//$NAME$|$ASIC$|$PORT$//num_voq` is never emitted.
- R705: **NO-FIRE (dead spine group)** - rooted at `SYSTEM_PORT`, which is not an OC root of this document, so no document data can supply this rule; `SYSTEM_PORT//$NAME$|$ASIC$|$PORT$//speed` is never emitted.
- R706: **NO-FIRE (dead spine group)** - rooted at `SYSTEM_PORT`, which is not an OC root of this document, so no document data can supply this rule; `SYSTEM_PORT//$NAME$|$ASIC$|$PORT$//switch_id` is never emitted.
- R707: **NO-FIRE (dead spine group)** - rooted at `SYSTEM_PORT`, which is not an OC root of this document, so no document data can supply this rule; `SYSTEM_PORT//$NAME$|$ASIC$|$PORT$//system_port_id` is never emitted.
### `BUFFER_POOL//BUFFER_POOL_LIST` - 4 rows, 0 firing, 0 lines

- R708: **NO-FIRE (dead spine group)** - rooted at `BUFFER_POOL`, which is not an OC root of this document, so no document data can supply this rule; `BUFFER_POOL//$NAME$//type` is never emitted.
- R709: **NO-FIRE (dead spine group)** - rooted at `BUFFER_POOL`, which is not an OC root of this document, so no document data can supply this rule; `BUFFER_POOL//$NAME$//mode` is never emitted.
- R710: **NO-FIRE (dead spine group)** - rooted at `BUFFER_POOL`, which is not an OC root of this document, so no document data can supply this rule; `BUFFER_POOL//$NAME$//size` is never emitted.
- R711: **NO-FIRE (dead spine group)** - rooted at `BUFFER_POOL`, which is not an OC root of this document, so no document data can supply this rule; `BUFFER_POOL//$NAME$//xoff` is never emitted.
### `DEVICE_METADATA//localhost` - 21 rows, 0 firing, 0 lines

- R712: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//hwsku` is never emitted.
- R713: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//default_bgp_status` is never emitted.
- R714: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//docker_routing_config_mode` is never emitted.
- R715: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//hostname` is never emitted.
- R716: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//platform` is never emitted.
- R717: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//asic` is never emitted.
- R718: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//mac` is never emitted.
- R719: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//arp_to_route` is never emitted.
- R720: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//nd_to_route` is never emitted.
- R721: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//default_pfcwd_status` is never emitted.
- R722: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//bgp_asn` is never emitted.
- R723: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//deployment_id` is never emitted.
- R724: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//type` is never emitted.
- R725: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//coalesce` is never emitted.
- R726: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//ndmask_v6` is never emitted.
- R727: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//asic_name` is never emitted.
- R728: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//max_cores` is never emitted.
- R729: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//switch_id` is never emitted.
- R730: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//switch_type` is never emitted.
- R731: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//vrf_leaking_route_map_v4` is never emitted.
- R732: **NO-FIRE (dead spine group)** - rooted at `DEVICE_METADATA`, which is not an OC root of this document, so no document data can supply this rule; `DEVICE_METADATA//localhost//vrf_leaking_route_map_v6` is never emitted.
### `YANG_VALIDATION//config` - 2 rows, 2 firing, 2 lines

- R733: fire (1 leaf, 1 line); YANG_VALIDATION|config|enable = "True"
- R734: fire (1 leaf, 1 line); YANG_VALIDATION|config|intercept = "True"
### `LLDP_GLOBAL//global` - 1 rows, 0 firing, 0 lines

- R735: **NO-FIRE (dead spine group)** - rooted at `LLDP_GLOBAL`, which is not an OC root of this document, so no document data can supply this rule; `LLDP_GLOBAL//global//mgmt_ip` is never emitted.
### `NTP//global` - 1 rows, 0 firing, 0 lines

- R736: **NO-FIRE (dead spine group)** - rooted at `NTP`, which is not an OC root of this document, so no document data can supply this rule; `NTP//global//direction` is never emitted.
### `SNMP//snmp` - 1 rows, 0 firing, 0 lines

- R737: **NO-FIRE (dead spine group)** - rooted at `SNMP`, which is not an OC root of this document, so no document data can supply this rule; `SNMP//snmp//direction` is never emitted.
### `TACPLUS//global` - 1 rows, 0 firing, 0 lines

- R738: **NO-FIRE (dead spine group)** - rooted at `TACPLUS`, which is not an OC root of this document, so no document data can supply this rule; `TACPLUS//global//src_ip` is never emitted.
### `SYSLOG_SERVER//syslog_server` - 2 rows, 0 firing, 0 lines

- R739: **NO-FIRE (dead spine group)** - rooted at `SYSLOG_SERVER`, which is not an OC root of this document, so no document data can supply this rule; `SYSLOG_SERVER//syslog_server//direction` is never emitted.
- R740: **NO-FIRE (dead spine group)** - rooted at `SYSLOG_SERVER`, which is not an OC root of this document, so no document data can supply this rule; `SYSLOG_SERVER//syslog_server//src_ip` is never emitted.
### `TELEMETRY//gnmi` - 1 rows, 0 firing, 0 lines

- R741: **NO-FIRE (dead spine group)** - rooted at `TELEMETRY`, which is not an OC root of this document, so no document data can supply this rule; `TELEMETRY//gnmi//gnmi_direction` is never emitted.
### `BUFFER_PROFILE//BUFFER_PROFILE_LIST` - 7 rows, 0 firing, 0 lines

- R742: **NO-FIRE (dead spine group)** - rooted at `BUFFER_PROFILE`, which is not an OC root of this document, so no document data can supply this rule; `BUFFER_PROFILE//$NAME$//static_th` is never emitted.
- R743: **NO-FIRE (dead spine group)** - rooted at `BUFFER_PROFILE`, which is not an OC root of this document, so no document data can supply this rule; `BUFFER_PROFILE//$NAME$//dynamic_th` is never emitted.
- R744: **NO-FIRE (dead spine group)** - rooted at `BUFFER_PROFILE`, which is not an OC root of this document, so no document data can supply this rule; `BUFFER_PROFILE//$NAME$//size` is never emitted.
- R745: **NO-FIRE (dead spine group)** - rooted at `BUFFER_PROFILE`, which is not an OC root of this document, so no document data can supply this rule; `BUFFER_PROFILE//$NAME$//pool` is never emitted.
- R746: **NO-FIRE (dead spine group)** - rooted at `BUFFER_PROFILE`, which is not an OC root of this document, so no document data can supply this rule; `BUFFER_PROFILE//$NAME$//xon_offset` is never emitted.
- R747: **NO-FIRE (dead spine group)** - rooted at `BUFFER_PROFILE`, which is not an OC root of this document, so no document data can supply this rule; `BUFFER_PROFILE//$NAME$//xon` is never emitted.
- R748: **NO-FIRE (dead spine group)** - rooted at `BUFFER_PROFILE`, which is not an OC root of this document, so no document data can supply this rule; `BUFFER_PROFILE//$NAME$//xoff` is never emitted.
### `BUFFER_QUEUE//BUFFER_QUEUE_LIST` - 1 rows, 0 firing, 0 lines

- R749: **NO-FIRE (dead spine group)** - rooted at `BUFFER_QUEUE`, which is not an OC root of this document, so no document data can supply this rule; `BUFFER_QUEUE//$PORT$|$QINDEX$//profile` is never emitted.
### `BGP_VRF//BGP_VRF_LIST` - 4 rows, 0 firing, 0 lines

- R750: **NO-FIRE (dead spine group)** - rooted at `BGP_VRF`, which is not an OC root of this document, so no document data can supply this rule; `BGP_VRF//$VRF$//bgp_asn` is never emitted.
- R751: **NO-FIRE (dead spine group)** - rooted at `BGP_VRF`, which is not an OC root of this document, so no document data can supply this rule; `BGP_VRF//$VRF$//coalesce` is never emitted.
- R752: **NO-FIRE (dead spine group)** - rooted at `BGP_VRF`, which is not an OC root of this document, so no document data can supply this rule; `BGP_VRF//$VRF$//vrf_leaking_route_map_v4` is never emitted.
- R753: **NO-FIRE (dead spine group)** - rooted at `BGP_VRF`, which is not an OC root of this document, so no document data can supply this rule; `BGP_VRF//$VRF$//vrf_leaking_route_map_v6` is never emitted.
### `BGP_VRF_LEAKING_IPV4//BGP_VRF_LEAKING_IPV4_LIST` - 1 rows, 0 firing, 0 lines

- R754: **NO-FIRE (dead spine group)** - rooted at `BGP_VRF_LEAKING_IPV4`, which is not an OC root of this document, so no document data can supply this rule; `BGP_VRF_LEAKING_IPV4//$TARGET-VRF$|$SOURCE-VRF$//import_vrf` is never emitted.
### `BGP_VRF_LEAKING_IPV6//BGP_VRF_LEAKING_IPV6_LIST` - 1 rows, 0 firing, 0 lines

- R755: **NO-FIRE (dead spine group)** - rooted at `BGP_VRF_LEAKING_IPV6`, which is not an OC root of this document, so no document data can supply this rule; `BGP_VRF_LEAKING_IPV6//$TARGET-VRF$|$SOURCE-VRF$//import_vrf` is never emitted.
### `PBR_NHG//PBR_NHG_LIST` - 1 rows, 0 firing, 0 lines

- R756: **NO-FIRE (dead spine group)** - rooted at `PBR_NHG`, which is not an OC root of this document, so no document data can supply this rule; `PBR_NHG//$PBR-NAME$` is never emitted.
### `PBR_NHG_MEMBER//PBR_NHG_MEMBER_INTF_LIST` - 1 rows, 0 firing, 0 lines

- R757: **NO-FIRE (dead spine group)** - rooted at `PBR_NHG_MEMBER`, which is not an OC root of this document, so no document data can supply this rule; `PBR_NHG_MEMBER//$PBR-NAME$|$NEXTHOP$@$INTF-NAME$` is never emitted.
### `PBR_NHG_MEMBER//PBR_NHG_MEMBER_LIST` - 1 rows, 0 firing, 0 lines

- R758: **NO-FIRE (dead spine group)** - rooted at `PBR_NHG_MEMBER`, which is not an OC root of this document, so no document data can supply this rule; `PBR_NHG_MEMBER//$PBR-NAME$|$NEXTHOP$` is never emitted.
### `PBR_RULE//PBR_RULE_LIST` - 9 rows, 0 firing, 0 lines

- R759: **NO-FIRE (dead spine group)** - rooted at `PBR_RULE`, which is not an OC root of this document, so no document data can supply this rule; `PBR_RULE//$RULE-ID$//DSCP` is never emitted.
- R760: **NO-FIRE (dead spine group)** - rooted at `PBR_RULE`, which is not an OC root of this document, so no document data can supply this rule; `PBR_RULE//$RULE-ID$//DST_IP` is never emitted.
- R761: **NO-FIRE (dead spine group)** - rooted at `PBR_RULE`, which is not an OC root of this document, so no document data can supply this rule; `PBR_RULE//$RULE-ID$//IN_PORT` is never emitted.
- R762: **NO-FIRE (dead spine group)** - rooted at `PBR_RULE`, which is not an OC root of this document, so no document data can supply this rule; `PBR_RULE//$RULE-ID$//IP_PROTOCOL` is never emitted.
- R763: **NO-FIRE (dead spine group)** - rooted at `PBR_RULE`, which is not an OC root of this document, so no document data can supply this rule; `PBR_RULE//$RULE-ID$//L4_DST_PORT` is never emitted.
- R764: **NO-FIRE (dead spine group)** - rooted at `PBR_RULE`, which is not an OC root of this document, so no document data can supply this rule; `PBR_RULE//$RULE-ID$//L4_SRC_PORT` is never emitted.
- R765: **NO-FIRE (dead spine group)** - rooted at `PBR_RULE`, which is not an OC root of this document, so no document data can supply this rule; `PBR_RULE//$RULE-ID$//PACKET_ACTION` is never emitted.
- R766: **NO-FIRE (dead spine group)** - rooted at `PBR_RULE`, which is not an OC root of this document, so no document data can supply this rule; `PBR_RULE//$RULE-ID$//PRIORITY` is never emitted.
- R767: **NO-FIRE (dead spine group)** - rooted at `PBR_RULE`, which is not an OC root of this document, so no document data can supply this rule; `PBR_RULE//$RULE-ID$//SRC_IP` is never emitted.
### `BUFFER_PG//BUFFER_PG_LIST` - 1 rows, 0 firing, 0 lines

- R768: **NO-FIRE (dead spine group)** - rooted at `BUFFER_PG`, which is not an OC root of this document, so no document data can supply this rule; `BUFFER_PG//$PORT$|$PG-NUM$//profile` is never emitted.

## 4. Dead-rule groups: uppercase-template spines

**These 75 rows can never fire on this document.** Their `yang_key` root is a SONiC table name that is not an OC root
(document roots: `stp`, `lldp`, `bfd`, `YANG_VALIDATION`, `int`, `default`, `relay-agent`, `lacp`, `acl`, `network-instances`, `components`, `qos`, `routing-policy`, `system`, `interfaces`), and no other rule or OC subtree can supply
the values - they exist only in a SONiC config, not in this OC document:

- `telemetry-system//global` (1 row 373-373): root `telemetry-system` absent from document.
- `telemetry-system//destination-groups` (1 row 374-374): root `telemetry-system` absent from document.
- `telemetry-system//subscriptions` (8 rows 375-382): root `telemetry-system` absent from document.
- `SYSTEM_PORT//SYSTEM_PORT_LIST` (6 rows 702-707): root `SYSTEM_PORT` absent from document.
- `BUFFER_POOL//BUFFER_POOL_LIST` (4 rows 708-711): root `BUFFER_POOL` absent from document.
- `DEVICE_METADATA//localhost` (21 rows 712-732): root `DEVICE_METADATA` absent from document.
- `LLDP_GLOBAL//global` (1 row 735-735): root `LLDP_GLOBAL` absent from document.
- `NTP//global` (1 row 736-736): root `NTP` absent from document.
- `SNMP//snmp` (1 row 737-737): root `SNMP` absent from document.
- `TACPLUS//global` (1 row 738-738): root `TACPLUS` absent from document.
- `SYSLOG_SERVER//syslog_server` (2 rows 739-740): root `SYSLOG_SERVER` absent from document.
- `TELEMETRY//gnmi` (1 row 741-741): root `TELEMETRY` absent from document.
- `BUFFER_PROFILE//BUFFER_PROFILE_LIST` (7 rows 742-748): root `BUFFER_PROFILE` absent from document.
- `BUFFER_QUEUE//BUFFER_QUEUE_LIST` (1 row 749-749): root `BUFFER_QUEUE` absent from document.
- `BGP_VRF//BGP_VRF_LIST` (4 rows 750-753): root `BGP_VRF` absent from document.
- `BGP_VRF_LEAKING_IPV4//BGP_VRF_LEAKING_IPV4_LIST` (1 row 754-754): root `BGP_VRF_LEAKING_IPV4` absent from document.
- `BGP_VRF_LEAKING_IPV6//BGP_VRF_LEAKING_IPV6_LIST` (1 row 755-755): root `BGP_VRF_LEAKING_IPV6` absent from document.
- `PBR_NHG//PBR_NHG_LIST` (1 row 756-756): root `PBR_NHG` absent from document.
- `PBR_NHG_MEMBER//PBR_NHG_MEMBER_INTF_LIST` (1 row 757-757): root `PBR_NHG_MEMBER` absent from document.
- `PBR_NHG_MEMBER//PBR_NHG_MEMBER_LIST` (1 row 758-758): root `PBR_NHG_MEMBER` absent from document.
- `PBR_RULE//PBR_RULE_LIST` (9 rows 759-767): root `PBR_RULE` absent from document.
- `BUFFER_PG//BUFFER_PG_LIST` (1 row 768-768): root `BUFFER_PG` absent from document.

Total dead rows in these groups: 75. Telemetry (`telemetry-system//*`, 10 rows) is included: the document has no
`telemetry-system` root, so the `TELEMETRY_CLIENT` table is never emitted. `DEVICE_METADATA//localhost` (21 rows) is
likewise dead as a *source* group - but note the DEVICE_METADATA table is still populated by this audit's rows
204/205/207/214/215/216 (`system//config`, `system//arp`, `system//nd`), so `DEVICE_METADATA|localhost` does appear in output.

## 5. `stp`, `bfd`, `default` roots

Searched all 769 rows: **zero rows have `stp`, `bfd` or `default` as their `yang_key` root** (the strings `bfd`/`default`
only occur inside `enable-bfd`/`default-*` field names under `network-instances`). Consequently the doc's
`stp/global/config/enabled`, all 11 `bfd/interfaces/interface/*` objects and `default/config/enable` have **no rule
coverage anywhere** - they can never be translated with this table.

## 6. Live-root groups with missing subtrees/leaves (dead on this document only)

These rows have a valid OC root but the specific path is absent. They would fire on a richer document; on this one they are dead.

- `system//overlay` (51 rows R297-R347): document `system` has no `overlay` child -> OVERLAY*/OVERLAY_SAMPLER/OVERLAY_ACL_RULE/OVERLAY_PORT/OVERLAY_TUNNEL tables never emitted.
- `system//hash` outer/inner/dlb/dhash (26 rows R229-R253): `system/hash` exists with `global/outer/inner`, but `algorithm-lag`, `lag-tunnel-hash`, `ecmp-tunnel-hash`, `*-hash-mode`, `hash-offset` and the whole `dlb`/`dhash` subtrees are absent. NB: the task brief's hypothesis of `system//hash` inner/outer factor rules (`list_value`/`list_2_string`/`string_combination`) is **false** - the CSV has no `factors` rows at all; only 3 hash rows fire (R225/R227/R228).
- `system//mirrors` (7), `system//mod` (3), `system//fcr` (5), `system//gnoi` (1), `system//breakout` (1): subtrees absent.
- `system//grpc` R218 (gnmi-direction), R219 (port), R223 (channel), `system//gnoi` R224: leaves absent (doc only has password/enable/tls-type/username).
- `system//config` R208 (asic-variant), R209 (asic), R212 (database-version), R213 (login-timeout): leaves absent.
- `system//aaa` R199 (`system/aaa/config/fail-through`): no `config` child under `system/aaa`.
- `system//snmp` R258 (`.../servers/server/$SERVER$/config/port`): SNMP servers have `address/type/version/key`, no `port`, so `SNMP_AGENT_ADDRESS_CONFIG` is never emitted.
- `system//counter` (14 rows): document has only 11 counter sections; `port-buffer-drop` (R268/R286), `rif` (R271/R290), `policer-stat` (R273/R292), `bridge` (R274/R293), `tunnel` (R275/R294), `debug` (R276/R295), `ebst` (R277/R296) are absent.
- `system//monitor-link` R187 (Bridge-Aggregation uplink): all 16 Bridge-Aggregation objects have only `downlink`; R190-R192 use lowercase `port-channel$INTERFACEID$` while the document uses `Bridge-Aggregation<N>` -> never match (the CamelCase rows R188/R189 cover those objects).
- `components//component` R687-R690 (`hbm`/`sms` slices: only `sliceall` exists), R680 (`input/queues/queue/queue5/config/profile` leaf absent; note the row's `sonic_key` also has a stray trailing apostrophe: `BUFFER_PG//$INTERFACE$|$QUEUEID$//profile'` - CSV inconsistency), R693-R697 (`dwdm` subtree absent).

## 7. OC paths in this area with NO covering rule

568 of 1089 scalar/list leaves under `system`, `components`, `YANG_VALIDATION` are unmatched by any
of the 769 rules. By 2nd-level section: `components/component` 263, `system/snmp` 76, `system/monitor-link` 67, `system/nd` 54, `system/sampling` 34, `system/logging` 26, `system/aaa` 23, `system/hash` 13, `system/ntp` 5, `system/config` 3, `system/ssh-server` 2, `system/clock` 1, `system/icmp` 1.

Most uncovered leaves are list-key/`name` artefacts, but these real settings are silently dropped (worth reporting as
support gaps; no rule exists to fix them faithfully):

- `components/component/buffer/integrated-circuit/chip/buffers/buffer/SHARED_BUFFER/interfaces/interface/*/output/queues/queue/*/config/limit-mode` (32 leaves) = `"DYNAMIC"`  (e.g. `components/component/buffer/integrated-circuit/chip/buffers/buffer/SHARED_BUFFER/interfaces/interface/Eth400GE27/output/queues/queue/queue5/config/limit-mode`)
- `components/component/buffer/integrated-circuit/chip/buffers/buffer/SHARED_BUFFER/interfaces/interface/*/input/queues/queue/*/config/limit-mode` (32 leaves) = `"DYNAMIC"`  (e.g. `components/component/buffer/integrated-circuit/chip/buffers/buffer/SHARED_BUFFER/interfaces/interface/Eth400GE27/input/queues/queue/queue5/config/limit-mode`)
- `components/component/buffer/integrated-circuit/chip/buffers/buffer/HEADROOM/interfaces/interface/*/input/queues/queue/*/config/limit-mode` (32 leaves) = `"STATIC"`  (e.g. `components/component/buffer/integrated-circuit/chip/buffers/buffer/HEADROOM/interfaces/interface/Eth400GE27/input/queues/queue/queue5/config/limit-mode`)
- `system/aaa/server-groups/server-group/tencent_scheme/servers/server/*/tacacs/config/source-address` (2 leaves) = `"22.156.39.15"`  (e.g. `system/aaa/server-groups/server-group/tencent_scheme/servers/server/172.16.0.196/tacacs/config/source-address`)
- `system/aaa/server-groups/server-group/tencent_scheme/servers/server/*/config/address` (2 leaves) = `"172.16.0.196"`  (e.g. `system/aaa/server-groups/server-group/tencent_scheme/servers/server/172.16.0.196/config/address`)
- `system/aaa/server-groups/server-group/tencent_scheme/servers/server/*/config/index` (2 leaves) = `"0"`  (e.g. `system/aaa/server-groups/server-group/tencent_scheme/servers/server/172.16.0.196/config/index`)
- `system/aaa/authentication/admin-user/config/admin-password` = `"tencent"`  (e.g. `system/aaa/authentication/admin-user/config/admin-password`)
- `system/aaa/authentication/users/user/tencent/config/password` = `"tencent"`  (e.g. `system/aaa/authentication/users/user/tencent/config/password`)
- `system/aaa/authentication/users/user/tencent/config/role` = `"network-admin"`  (e.g. `system/aaa/authentication/users/user/tencent/config/role`)
- `system/aaa/authentication/users/user/tencent/config/username` = `"tencent"`  (e.g. `system/aaa/authentication/users/user/tencent/config/username`)
- `system/ntp/config/ntp-source-address` = `"22.156.39.15"`  (e.g. `system/ntp/config/ntp-source-address`)
- `system/ntp/config/source-interface` = `"eth0"`  (e.g. `system/ntp/config/source-interface`)
- `system/ntp/config/enabled` = `"true"`  (e.g. `system/ntp/config/enabled`)
- `system/snmp/servers/server/*/config/address` (12 leaves) = `"172.16.0.197"`  (e.g. `system/snmp/servers/server/172.16.0.197/config/address`)
- `system/snmp/servers/server/*/config/type` (12 leaves) = `"trap"`  (e.g. `system/snmp/servers/server/172.16.0.197/config/type`)
- `system/snmp/servers/server/*/config/version` (12 leaves) = `"v2c"`  (e.g. `system/snmp/servers/server/172.16.0.197/config/version`)
- `system/snmp/servers/server/*/config/key` (12 leaves) = `"tcnw"`  (e.g. `system/snmp/servers/server/172.16.0.197/config/key`)
- `system/snmp/config/version` = `"v2c"`  (e.g. `system/snmp/config/version`)
- `system/snmp/communities/community/tcnw/config/filter` = `"SNMP-Filter"`  (e.g. `system/snmp/communities/community/tcnw/config/filter`)
- `system/snmp/communities/community/tcnw/config/mode` = `"read"`  (e.g. `system/snmp/communities/community/tcnw/config/mode`)
- `system/clock/config/timezone-name` = `"BeiJing 08:00:00"`  (e.g. `system/clock/config/timezone-name`)
- `system/icmp/config/ip-ttl-expire` = `"true"`  (e.g. `system/icmp/config/ip-ttl-expire`)
- `system/monitor-link/groups/group/*/downlink/config/up-delay` = `"120"`  (e.g. `system/monitor-link/groups/group/1/downlink/config/up-delay`)
- `system/nd/interfaces/interface/*/config/rate-limit` (16 leaves) = `"50"`  (e.g. `system/nd/interfaces/interface/Eth200GE9/config/rate-limit`)
- `system/nd/interfaces/interface/vlan 2/config/na-auto-learning` = `"true"`  (e.g. `system/nd/interfaces/interface/vlan 2/config/na-auto-learning`)
- `system/nd/interfaces/interface/vlan 2/config/nud-reachable-time` = `"1000"`  (e.g. `system/nd/interfaces/interface/vlan 2/config/nud-reachable-time`)
- `system/nd/interfaces/interface/vlan 2/config/stale-time` = `"90"`  (e.g. `system/nd/interfaces/interface/vlan 2/config/stale-time`)
- `system/nd/config/stale-time` = `"300"`  (e.g. `system/nd/config/stale-time`)
- `system/ssh-server/config/enable` = `"true"`  (e.g. `system/ssh-server/config/enable`)
- `system/ssh-server/config/filters` = `["SSH-Filter", "SSH-Filter-IPv6"]`  (e.g. `system/ssh-server/config/filters`)
- `system/logging/remote-servers/remote-server/*/selectors/selector/LOCAL2 INFORMATIONAL/config/facility` (4 leaves) = `"LOCAL2"`  (e.g. `system/logging/remote-servers/remote-server/22.144.124.133/selectors/selector/LOCAL2 INFORMATIONAL/config/facility`)
- `system/logging/config/buffer-size` = `"1024"`  (e.g. `system/logging/config/buffer-size`)
- `system/logging/config/source-interface` = `"eth0"`  (e.g. `system/logging/config/source-interface`)
- `system/config/domain-name` = `"tencent_domain"`  (e.g. `system/config/domain-name`)
- `system/config/route-mode` = `"ipv6-128"`  (e.g. `system/config/route-mode`)
- `system/config/switch-mode` = `"dual-stack"`  (e.g. `system/config/switch-mode`)
- `system/hash/outer/config/enable` = `"true"`  (e.g. `system/hash/outer/config/enable`)
- `system/hash/outer/factors/config/src-ip` = `"true"`  (e.g. `system/hash/outer/factors/config/src-ip`)
- `system/hash/outer/factors/config/dst-ip` = `"true"`  (e.g. `system/hash/outer/factors/config/dst-ip`)
- `system/hash/outer/factors/config/protocol` = `"true"`  (e.g. `system/hash/outer/factors/config/protocol`)
- `system/hash/outer/factors/config/src-port` = `"true"`  (e.g. `system/hash/outer/factors/config/src-port`)
- `system/hash/outer/factors/config/dst-port` = `"true"`  (e.g. `system/hash/outer/factors/config/dst-port`)
- `system/hash/global/config/mode` = `"per-flow"`  (e.g. `system/hash/global/config/mode`)
- `system/hash/inner/config/enable` = `"true"`  (e.g. `system/hash/inner/config/enable`)
- `system/hash/inner/factors/config/dst-ip` = `"true"`  (e.g. `system/hash/inner/factors/config/dst-ip`)
- `system/hash/inner/factors/config/src-ip` = `"true"`  (e.g. `system/hash/inner/factors/config/src-ip`)
- `system/hash/inner/factors/config/protocol` = `"true"`  (e.g. `system/hash/inner/factors/config/protocol`)
- `system/hash/inner/factors/config/src-port` = `"true"`  (e.g. `system/hash/inner/factors/config/src-port`)
- `system/hash/inner/factors/config/dst-port` = `"true"`  (e.g. `system/hash/inner/factors/config/dst-port`)

Note: `system/monitor-link/groups/group/*/downlink/config/up-delay` is not emitted by itself, but it is read by the
`ockey` lookup of rows 188/193/194 (contract §3.1) - it supplies all `updelaytime = "120"` values. Also completely uncovered:
`system/clock` (`timezone-name`), `system/icmp` (`ip-ttl-expire`), `system/ssh-server` (`enable`, `filters`),
`system/nd/config/stale-time`, `system/nd/interfaces/*`, `system/ntp/config/*`, `system/snmp/config/version`,
SNMP server `type`/`version`/`key`, `system/aaa` users/admin-user, and `components/component/buffer/properties/property/*`.

## 8. Coverage / collision checks

- No rule belonging to another audit spine matches any `system`/`components`/`YANG_VALIDATION` leaf (verified over all
  769 rules), so this audit's 738 lines are disjoint from the other auditors' groups.
- Cross-table collision check on my emitted fields: `PORTCHANNEL|PortChannel*`/`PORT|Eth*` fields from monitor-link
  (`updelaytime/linkmode/groupid/option/threshold`) are not emitted by any other rule row, so they simply merge with the
  interfaces//interface group's PORT/PORTCHANNEL fields.
- `BUFFER_POOL|ingress_lossy_pool` appears from this audit only (rows 673-676); the uppercase `BUFFER_POOL//*` rows 708-711
  are dead, so they cannot overwrite it.

## 9. Diff against the engine output (snapshot)

Snapshot of `outputs/CQ-JLDC-2203-D05-TCS84R-LA200G-019.sonic.json` (sha256 `1f5ca41fe619287d69614595a1b4b25e481b2cc89fd5c67278e81722932575fd`); the engine may be newer than this audit.

- expected lines: 738; present in engine output: 738; value-identical: 706; differing: 32.
- differing fields (value in engine -> value in expected):
  - `BUFFER_PROFILE|...|dynamic_th` x32: engine `"0"` vs expected `"-3"` (e.g. `BUFFER_PROFILE|ingress_profile_Eth200GE10_5|dynamic_th`)

Interpretation: all 738 lines already agree with the engine except the 32 `ingress_profile_*_5|dynamic_th` entries, where
the engine computes `log2(int('1/8'))` -> `_as_int` falls back to 0 -> `"0"`, while the rule (`compute`, `log2(original)`)
means log2(1/8) = **-3**. That is an engine bug, not an audit disagreement; the expected file keeps `-3`.

## 10. Remaining open questions

1. **Engine bug (fix in translator):** `compute`/`log2(original)` on a fractional OC value must not go through int parsing;
   `1/8` must yield `-3` (32 expected lines differ only here). Suggest handling `<a>/<b>` as a Fraction before log2.
2. C1 `list_combination`: the engine already accumulates correctly (DNS / syslog / `ip_range` all agree) - update contract
   §3.2 wording so the engine does not regress to the "raw string" reading.
3. C2 reference notation: bare-key output is confirmed for the buffer rows (engine agrees); qos rows 610-617 use the same
   `[TABLE|KEY]` notation but SONiC often stores `PORT_QOS_MAP` map references qualified (`DSCP_TO_TC_MAP|name`) - review
   those rows (other auditor's scope) for qualified-vs-bare output.
4. C3 specificity: engine currently resolves like this audit (no `PORT|Bridge-Aggregation*`); keep the "literal characters"
   or "segment containing literal text" metric; a strict fully-literal-segment count would add 80 lines.
5. C7 `SYSLOG_SERVER|syslog_server|level` is a constant key with no per-server key and is order-dependent (`notice` -> `info`);
   `DNS|server|ip` and `SYSLOG_SERVER|...|servers` are aggregate lists under constant keys - confirm the reference format
   really stores them that way (both match the current engine, so this is a reference-answer risk only).
6. Dead coverage: roots `stp`/`bfd`/`default` have no rule rows at all, and the 75 uppercase-spine rows can never fire; no
   amount of engine work will produce those tables from this document.
