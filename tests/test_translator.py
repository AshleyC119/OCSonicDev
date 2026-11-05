"""Unit tests for the OC -> SONiC translator.

Run with:  python -m unittest discover -s tests -v
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from translator.cli import translate  # noqa: E402
from translator.engine import Translator  # noqa: E402
from translator.ocdoc import OcDocument  # noqa: E402
from translator.rules import load_rules  # noqa: E402

RULES = ROOT / "references" / "raw" / "yang2sonic_maptable(1).csv"
OC = ROOT / "data" / "raw" / "oc" / "CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt"
MANIFEST = ROOT / "data" / "manifest.json"


def run_translation(oc_data: dict) -> tuple[dict, Translator]:
    rules = load_rules(str(RULES))
    doc = OcDocument(oc_data)
    translator = Translator(rules, doc)
    return translator.translate(), translator


class MaterialsTest(unittest.TestCase):
    def test_raw_material_hashes_are_unchanged(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for item in manifest["files"]:
            data = (ROOT / item["path"]).read_bytes()
            self.assertEqual(len(data), item["bytes"], item["path"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"], item["path"])

    def test_real_document_translates_without_errors(self):
        config, report = translate(RULES, OC)
        self.assertIn("PORT", config)
        self.assertGreater(len(config), 20)

    def test_output_is_json_clean_and_deterministic(self):
        first, _ = translate(RULES, OC)
        second, _ = translate(RULES, OC)
        self.assertEqual(
            json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True)
        )

        def check(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertIsInstance(key, str)
                    check(item)
            elif isinstance(value, list):
                for item in value:
                    check(item)
            else:
                self.assertIsInstance(value, str)

        check(first)
        # every table/key/field must be a JSON object with string keys
        for table, keys in first.items():
            self.assertIsInstance(keys, dict, table)
            for key, fields in keys.items():
                self.assertIsInstance(key, str, table)
                if not isinstance(fields, dict):
                    self.assertEqual(fields, {}, f"{table}|{key}")


class PatternMatchingTest(unittest.TestCase):
    def test_specific_rule_shadows_generic_one(self):
        doc = {
            "interfaces": {
                "interface": {
                    "eth0": {"config": {"enabled": "true"}},
                    "Eth1": {"config": {"enabled": "true"}},
                }
            }
        }
        config, _ = run_translation(doc)
        # eth0 has an explicit suppression rule, Eth1 maps through $INTERFACE$
        self.assertNotIn("eth0", config.get("PORT", {}))
        self.assertEqual(config["PORT"]["Eth1"]["admin_status"], "up")

    def test_enum_mapping(self):
        doc = {"lldp": {"interfaces": {"interface": {"Eth1": {"config": {"admin-status": "all"}}}}}}
        config, _ = run_translation(doc)
        self.assertEqual(config["PORT"]["Eth1"]["lldp_status"], "rx-and-tx")


class ComputeTest(unittest.TestCase):
    def test_speed_divided_by_1000(self):
        doc = {
            "interfaces": {
                "interface": {
                    "Eth1": {
                        "ethernet": {"config": {"port-speed": "400000000"}},
                        "config": {"enabled": "true"},
                    }
                }
            }
        }
        config, _ = run_translation(doc)
        self.assertEqual(config["PORT"]["Eth1"]["speed"], "400000")

    def test_acl_priority_is_10000_minus_sequence(self):
        doc = {
            "acl": {
                "acl-sets": {
                    "acl-set": {
                        "T ACL_IPV4": {
                            "name": "T",
                            "type": "ACL_IPV4",
                            "config": {"name": "T", "type": "ACL_IPV4"},
                            "acl-entries": {
                                "acl-entry": {
                                    "20": {
                                        "config": {"sequence-id": "20"},
                                        "actions": {"config": {"forwarding-action": "permit"}},
                                        "ipv4": {"config": {"protocol": "tcp"}},
                                    }
                                }
                            },
                        }
                    }
                }
            }
        }
        config, _ = run_translation(doc)
        rule = config["ACL_RULE"]["T|RULE_20"]
        self.assertEqual(rule["PRIORITY"], "9980")
        # generic ACL rules map permit -> FORWARD for non control-plane sets
        self.assertEqual(rule["PACKET_ACTION"], "FORWARD")
        self.assertEqual(rule["IP_PROTOCOL"], "6")

    def test_hold_time_milliseconds_to_seconds(self):
        doc = {
            "interfaces": {
                "interface": {
                    "Eth1": {
                        "hold-time": {"config": {"up": "3000"}},
                        "config": {"enabled": "true"},
                    }
                }
            }
        }
        config, _ = run_translation(doc)
        self.assertEqual(config["PORT"]["Eth1"]["up_delay_interval"], "3")


class ListTest(unittest.TestCase):
    def test_dns_servers_accumulate_into_a_json_list(self):
        doc = {
            "system": {
                "dns": {
                    "servers": {
                        "server": {
                            "9.9.9.9": {"address": "9.9.9.9"},
                            "8.8.8.8": {"address": "8.8.8.8"},
                        }
                    }
                }
            }
        }
        config, _ = run_translation(doc)
        self.assertEqual(sorted(config["DNS"]["server"]["ip"]), ["8.8.8.8", "9.9.9.9"])

    def test_trunk_vlans_expand_and_accumulate_members(self):
        doc = {
            "interfaces": {
                "interface": {
                    "Eth1": {
                        "config": {"enabled": "true"},
                        "ethernet": {
                            "switched-vlan": {
                                "config": {
                                    "interface-mode": "trunk",
                                    "trunk-vlans": "10-12",
                                    "native-vlan": "10",
                                }
                            }
                        },
                    }
                }
            }
        }
        config, _ = run_translation(doc)
        self.assertEqual(sorted(config["VLAN"]), ["Vlan10", "Vlan11", "Vlan12"])
        self.assertEqual(config["VLAN_MEMBER"]["Vlan10|Eth1"]["tagging_mode"], "untagged")
        self.assertEqual(config["VLAN"]["Vlan12"]["members"], ["Eth1"])


class OckeyTest(unittest.TestCase):
    def test_management_interface_gateway_comes_from_static_route(self):
        doc = {
            "interfaces": {
                "interface": {
                    "eth0": {
                        "config": {"enabled": "true"},
                        "subinterfaces": {
                            "subinterface": {
                                "0": {
                                    "ipv4": {
                                        "addresses": {
                                            "address": {
                                                "10.0.0.2": {
                                                    "ip": "10.0.0.2",
                                                    "config": {"prefix-length": "24"},
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            },
            "network-instances": {
                "network-instance": {
                    "mgt_vrf": {
                        "protocols": {
                            "protocol": {
                                "STATIC STATIC": {
                                    "static-routes": {
                                        "static": {
                                            "0.0.0.0/0": {
                                                "next-hops": {
                                                    "next-hop": {
                                                        "1": {
                                                            "config": {"next-hop": "10.0.0.1"}
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
        }
        config, _ = run_translation(doc)
        self.assertEqual(
            config["MGMT_INTERFACE"]["eth0|10.0.0.2/24"]["gwaddr"], "10.0.0.1"
        )


class EmptyDictTest(unittest.TestCase):
    def test_loopback_address_creates_empty_object_key(self):
        doc = {
            "interfaces": {
                "interface": {
                    "Loopback0": {
                        "config": {"enabled": "true"},
                        "subinterfaces": {
                            "subinterface": {
                                "0": {
                                    "ipv4": {
                                        "addresses": {
                                            "address": {
                                                "1.1.1.1": {
                                                    "ip": "1.1.1.1",
                                                    "config": {"prefix-length": "32"},
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            }
        }
        config, _ = run_translation(doc)
        self.assertIn("Loopback0|1.1.1.1/32", config["LOOPBACK_INTERFACE"])
        self.assertEqual(
            config["LOOPBACK_INTERFACE"]["Loopback0|1.1.1.1/32"]["type"], "primary"
        )
        self.assertEqual(config["LOOPBACK"]["Loopback0"]["admin_status"], "up")


class FieldNameTest(unittest.TestCase):
    """Field names must never be value-substituted (``DNS|server|ip`` stays ip)."""

    def test_dns_field_named_ip(self):
        doc = {
            "system": {
                "dns": {"servers": {"server": {"1.1.1.1": {"address": "1.1.1.1"}}}}
            }
        }
        config, _ = run_translation(doc)
        self.assertEqual(config["DNS"]["server"]["ip"], ["1.1.1.1"])

    def test_bmc_gateway_ip_is_copied_verbatim(self):
        doc = {
            "interfaces": {
                "interface": {
                    "BMC": {
                        "name": "BMC",
                        "config": {"enabled": "true"},
                        "bmc": {"config": {"gateway-ip": "10.1.2.3"}},
                        "subinterfaces": {
                            "subinterface": {
                                "0": {
                                    "ipv4": {
                                        "addresses": {
                                            "address": {
                                                "10.1.2.9": {
                                                    "ip": "10.1.2.9",
                                                    "config": {"prefix-length": "24"},
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            }
        }
        config, _ = run_translation(doc)
        # the BMC rows use a literal key name "INTERFACE" (no $VAR$ placeholder)
        self.assertEqual(config["BMC"]["INTERFACE"]["defgw"], "10.1.2.3")
        self.assertEqual(config["BMC"]["INTERFACE"]["ipmask"], "10.1.2.9/24")


if __name__ == "__main__":
    unittest.main()
