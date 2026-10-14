"""CI test: rules.json must reproduce the saved values on both fixtures."""
import json
import sys
from pathlib import Path

from autorepair import extract
from repair import matches
from run import FIELDS

rules = json.loads(Path("rules.json").read_text())["rules"]
expected = json.loads(Path("fixtures/expected.json").read_text())
ok = True
for name, want in expected.items():
    got = extract(Path(f"fixtures/{name}.html").read_text(encoding="utf-8"),
                  rules)
    for field, spec in FIELDS.items():
        good = matches(got[field], want[field], spec["type"])
        ok &= good
        print(f"{name:8} {field:12} {'ok  ' if good else 'FAIL'} "
              f"got={got[field]!r} want={want[field]!r}")
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
