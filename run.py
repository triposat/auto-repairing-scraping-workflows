import json
import os
import sys
from datetime import date
from pathlib import Path

from scrapingbee import ScrapingBeeClient

from autorepair import extract, validate
from fetch import fetch
from repair import repair

FIELDS = {
    "description": {"type": "str",
                    "description": "short description in the About sidebar,"
                                   " not the README"},
    "stars": {"type": "int",
              "description": "number of stars in the About sidebar"},
    "forks": {"type": "int",
              "description": "number of forks in the About sidebar"},
    "watchers": {"type": "int",
                 "description": "number of watchers in the About sidebar"},
}
TARGET = {"url": "https://github.com/SeleniumHQ/selenium",
          "anchor": "SeleniumHQ/selenium", "wait_css": "main",
          "fetch_params": {"render_js": False}}
HOLDOUT = {"url": "https://github.com/SeleniumHQ/seleniumhq.github.io",
           "anchor": "SeleniumHQ/seleniumhq.github.io", "wait_css": "main",
           "fetch_params": {"render_js": False}}
OPTIONAL = [name for name, spec in FIELDS.items() if spec.get("optional")]
RULES, LAST_GOOD = Path("rules.json"), Path("last_good.json")


def main():
    client = ScrapingBeeClient(api_key=os.environ["SCRAPINGBEE_API_KEY"])
    store = json.loads(RULES.read_text())
    last_good = json.loads(LAST_GOOD.read_text())

    html, source = fetch(client, TARGET)
    record = extract(html, store["rules"])
    broken = validate(record, last_good, OPTIONAL)
    print(f"fetched via {source}, broken fields: {broken}")

    if broken:
        hold_html, _ = fetch(client, HOLDOUT)
        promoted, report = repair(
            client, FIELDS, broken,
            page={**TARGET, "html": html},
            holdout={**HOLDOUT, "html": hold_html})
        for field, outcome in report.items():
            print(f"  {field}: {outcome}")
        if promoted:
            store["history"].append({"version": store["version"],
                                     "rules": dict(store["rules"])})
            store["rules"].update(promoted)
            store["version"] += 1
            RULES.write_text(json.dumps(store, indent=2))
            record = extract(html, store["rules"])
            broken = validate(record, last_good, OPTIONAL)

    print(json.dumps(record, indent=2))
    if broken:
        Path("needs_review.json").write_text(json.dumps(
            {"url": TARGET["url"], "fields": broken, "record": record},
            indent=2))
        sys.exit(f"needs human review: {broken}")
    LAST_GOOD.write_text(json.dumps(
        {"date": date.today().isoformat(), "values": record}, indent=2))


if __name__ == "__main__":
    main()
