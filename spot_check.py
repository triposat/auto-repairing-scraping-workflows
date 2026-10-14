"""Audit saved rules: compare them with AI extraction on a sample of pages."""
import random

from autorepair import extract
from repair import ai_values, coerce, matches


def spot_check(client, pages, fields, rules, sample=3):
    """Return (url, field, rule value, AI value) for every disagreement."""
    problems = []
    for page in random.sample(pages, min(sample, len(pages))):
        got = extract(page["html"], rules)
        want = ai_values(client, page["url"], fields, page["fetch_params"])
        for field, spec in fields.items():
            ai = coerce(want.get(field), spec["type"])
            if ai is not None and not matches(got[field], ai, spec["type"]):
                problems.append((page["url"], field, got[field], ai))
    return problems
