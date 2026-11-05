import csv, ast, json
p = r"references/raw/yang2sonic_maptable(1).csv"
rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
mine = {
 "system//", "components//component", "YANG_VALIDATION//config", "DEVICE_METADATA//localhost",
 "LLDP_GLOBAL//global", "NTP//global", "SNMP//snmp", "TACPLUS//global",
 "SYSLOG_SERVER//syslog_server", "TELEMETRY//gnmi", "telemetry-system//",
 "SYSTEM_PORT//", "BUFFER_POOL//", "BUFFER_PROFILE//", "BUFFER_QUEUE//", "BUFFER_PG//",
 "PBR_RULE//", "PBR_NHG//", "PBR_NHG_MEMBER//", "BGP_VRF//", "BGP_VRF_LEAKING_IPV4//", "BGP_VRF_LEAKING_IPV6//",
}
out = []
for i,r in enumerate(rows):
    spi = r["spine"]
    hit = any(spi == m or spi.startswith(m) for m in mine)
    if not hit: continue
    out.append(f"=== ROW {i} | spine={spi}")
    out.append(f"  yang_key   = {r['yang_key']}")
    out.append(f"  yang_value = {r['yang_value']}")
    out.append(f"  sonic_key  = {r['sonic_key']}")
    out.append(f"  sonic_value= {r['sonic_value']}")
print(len(out)//5, "rows dumped")
open("tmp_sys_rows.txt","w",encoding="utf-8").write("\n".join(out))
