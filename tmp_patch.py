from pathlib import Path
p=Path('tests/test_translator.py'); s=p.read_text(encoding='utf-8')
s=s.replace('        self.assertEqual(rule["PACKET_ACTION"], "ACCEPT")','        # generic ACL rules map permit -> FORWARD for non control-plane sets\n        self.assertEqual(rule["PACKET_ACTION"], "FORWARD")')
s=s.replace('        self.assertEqual(config["LOOPBACK_INTERFACE"]["Loopback0|1.1.1.1/32"], {})','        self.assertIn("Loopback0|1.1.1.1/32", config["LOOPBACK_INTERFACE"])\n        self.assertEqual(\n            config["LOOPBACK_INTERFACE"]["Loopback0|1.1.1.1/32"]["type"], "primary"\n        )')
p.write_text(s,encoding='utf-8')
