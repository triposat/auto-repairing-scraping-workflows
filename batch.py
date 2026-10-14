"""Run one template as a batch: repair each broken field once, not per page."""
import json
from pathlib import Path

from autorepair import check_batch, extract
from fetch import fetch
from repair import repair


def run_batch(client, pages, fields, rules_path=Path("rules.json")):
    store = json.loads(rules_path.read_text())
    html = {}
    for page in pages:
        try:
            html[page["url"]], _ = fetch(client, page)
        except RuntimeError as error:
            print(error)  # a lost row, which check_batch() counts
    records = {url: extract(h, store["rules"]) for url, h in html.items()}

    # A field that is null on at least half the pages broke for the template.
    nulls = {f: sum(r[f] is None for r in records.values()) for f in fields}
    broken = [f for f in fields if 2 * nulls[f] >= len(records)]
    failing = [p for p in pages if p["url"] in records
               and any(records[p["url"]][f] is None for f in broken)]
    print(f"{len(records)} pages, broken for the template: {broken}")
    if broken and len(failing) >= 2:
        target, holdout = failing[:2]  # 2 pages of the batch, 2 values
        promoted, report = repair(
            client, fields, broken,
            page={**target, "html": html[target["url"]]},
            holdout={**holdout, "html": html[holdout["url"]]})
        for field, outcome in report.items():
            print(f"  {field}: {outcome}")
        if promoted:
            store["history"].append({"version": store["version"],
                                     "rules": dict(store["rules"])})
            store["rules"].update(promoted)
            store["version"] += 1
            rules_path.write_text(json.dumps(store, indent=2))
            records = {url: extract(h, store["rules"])
                       for url, h in html.items()}

    required = [f for f, spec in fields.items() if not spec.get("optional")]
    problems = check_batch(list(records.values()), required, len(pages))
    print(f"problems after repair: {problems}")
    return records, problems
