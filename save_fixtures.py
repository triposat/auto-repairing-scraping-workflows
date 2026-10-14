import json
import os
from pathlib import Path

from scrapingbee import ScrapingBeeClient

from fetch import fetch
from repair import ai_values, coerce
from run import FIELDS, HOLDOUT, TARGET

client = ScrapingBeeClient(api_key=os.environ["SCRAPINGBEE_API_KEY"])
Path("fixtures").mkdir(exist_ok=True)
expected = {}
for name, page in (("target", TARGET), ("holdout", HOLDOUT)):
    html, _ = fetch(client, page)  # the content check rejects block pages
    Path(f"fixtures/{name}.html").write_text(html, encoding="utf-8")
    values = ai_values(client, page["url"], FIELDS, page["fetch_params"])
    expected[name] = {f: coerce(values.get(f), spec["type"])
                      for f, spec in FIELDS.items()}
    missing = [f for f, v in expected[name].items() if v is None]
    if missing:
        raise SystemExit(
            f"{name}: no value for {missing}, make each description specific")
Path("fixtures/expected.json").write_text(json.dumps(expected, indent=2))
print(json.dumps(expected, indent=2))
