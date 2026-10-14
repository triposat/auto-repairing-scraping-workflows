import json
import re
from datetime import date

from parsel import Selector

NUM_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*([kKmM])?(?![\w])")
NUMERIC = ("int", "decimal")


def numbers_in(text, ftype="int"):
    """'33,853' -> [(33853, True)]. '33.9k' -> [(33900, False)].

    The flag says whether the number has full precision. Decimal fields
    keep the fraction: '$1,299.99' -> [(1299.99, True)].
    """
    found = []
    for digits, suffix in NUM_RE.findall(text or ""):
        n = float(digits.replace(",", ""))
        if suffix:
            n *= 1_000 if suffix in "kK" else 1_000_000
        found.append((round(n) if ftype == "int" else n, not suffix))
    return found


def walk_json(data, path):
    for key in path:
        try:
            data = data[key]
        except (KeyError, IndexError, TypeError):
            return None
    return data


def apply_rule(sel, rule):
    if rule.get("xpath"):
        nodes = sel.xpath(rule["xpath"])
    else:
        nodes = sel.css(rule["css"])
    if not nodes:
        return None
    if rule.get("json_path"):
        try:
            payload = json.loads(nodes[0].css("::text").get() or "")
        except json.JSONDecodeError:
            return None
        raw = walk_json(payload, rule["json_path"])
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            raw = str(raw)  # parse it like page text
        raw = raw if isinstance(raw, str) else None
    elif rule.get("attr"):
        raw = nodes[0].attrib.get(rule["attr"])
    else:
        raw = " ".join(t.strip() for t in nodes[0].css("::text").getall())
    if not raw:
        return None
    if rule["type"] in NUMERIC:
        exact = [n for n, full in numbers_in(raw, rule["type"]) if full]
        return exact[0] if exact else None  # reject "33.9k"
    return " ".join(raw.split()) or None


def extract(html, rules):
    sel = Selector(text=html)
    return {field: apply_rule(sel, rule) for field, rule in rules.items()}


def validate(record, last_good, optional=(), max_jump=0.5, max_age_days=7):
    """Return the fields that need repair: nulls and implausible jumps.

    A null in an optional field is a missing value, not a broken rule. A
    baseline older than max_age_days cannot judge a jump, so only nulls
    count there.
    """
    since = date.fromisoformat(last_good.get("date", "1970-01-01"))
    fresh = (date.today() - since).days <= max_age_days
    baseline = last_good.get("values", {}) if fresh else {}
    broken = []
    for field, value in record.items():
        prev = baseline.get(field)
        if value is None:
            if field not in optional:
                broken.append(field)
        elif isinstance(value, (int, float)) and prev:
            if abs(value - prev) / prev > max_jump:
                broken.append(field)
    return broken


def check_batch(records, fields, expected_rows, max_null_rate=0.05,
                min_share=0.5):
    """Catch what one record cannot show: lost rows and rising null rates."""
    problems = []
    if len(records) < expected_rows * min_share:
        problems.append(f"rows: {len(records)} of about {expected_rows}")
    for field in fields:
        nulls = sum(r.get(field) is None for r in records)
        if records and nulls / len(records) > max_null_rate:
            problems.append(f"{field}: {nulls} of {len(records)} null")
    return problems
