#!/usr/bin/env python3
"""Debug: check what matches and what doesn't."""
import os, re, logging
from dotenv import load_dotenv
from request_api import RentmanClient

load_dotenv()
logging.basicConfig(level=logging.WARNING)

token = os.getenv("RENTMAN_TOKEN", "")
client = RentmanClient(token=token, project=791)

eq = client.get_project_equipment()
serial_ids = client.extract_serial_ids(eq)
sn = client.get_serial_number_info(serial_ids)

# Build match set same way app does
match_set = set()
for s in sn:
    for key in ("id", "qrcodes", "serial", "displayname"):
        val = s.get(key)
        if val is None:
            continue
        for part in str(val).split(","):
            part = part.strip()
            if part:
                match_set.add(part)
match_set.discard("")

print(f"Match set size: {len(match_set)}")

# Check specific values
test_codes = ["F105685", "C1164667", "F119656"]
for code in test_codes:
    found = code in match_set
    print(f"  {code} in match_set? {found}")

# Check if C-prefixed codes exist at all
c_codes = [v for v in match_set if v.startswith("C")]
print(f"\nC-prefixed codes in match set: {len(c_codes)}")
if c_codes:
    print(f"  Samples: {list(c_codes)[:10]}")

# Check all prefixes
prefixes = {}
for v in match_set:
    prefix = v[0] if v else "?"
    prefixes[prefix] = prefixes.get(prefix, 0) + 1
print(f"\nMatch set by first character: {dict(sorted(prefixes.items()))}")

# Check what fields contain C-prefixed values
print("\n--- Checking serial number fields for C-prefix values ---")
c_fields = {}
for s in sn:
    for key in ("id", "qrcodes", "serial", "displayname", "ref"):
        val = str(s.get(key, ""))
        if "C1164667" in val:
            c_fields[key] = val
            print(f"  Found C1164667 in field '{key}': {val}")
if not c_fields:
    print("  C1164667 NOT FOUND in any serial number record.")
