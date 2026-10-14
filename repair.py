import json
import re

from cssselect import SelectorError
from lxml import html as lxml_html
from parsel import Selector

from autorepair import NUMERIC, apply_rule, numbers_in

VALUE_ATTRS = ("title", "aria-label", "content", "value", "datetime")
SKIP_TAGS = {"script", "style", "noscript", "svg", "path"}
JSON_SCRIPTS = ('script[type="application/json"], '
                'script[type="application/ld+json"]')
# Generated IDs and CSS-module hashes (Sidebar__description__xTkIP) change
# with every deploy.
UNSTABLE = re.compile(
    r"[0-9a-f]{8,}|\d{4,}|^(ember|react|:r)"
    r"|(__|-)(?=\w*[A-Z0-9])(?=\w*[a-z])[A-Za-z0-9]{5}$")
# Tailwind classes such as hover:underline are not plain CSS names.
CSS_NAME = re.compile(r"-?[A-Za-z_][\w-]*")


def ai_values(client, url, fields, fetch_params, tries=2):
    """Ask ScrapingBee AI extraction for the value of each field."""
    values, missing = {}, list(fields)
    for _ in range(tries):
        rules = {
            name: {"description": fields[name]["description"],
                   "type": ("number" if fields[name]["type"] in NUMERIC
                            else "string")}
            for name in missing
        }
        params = {"ai_extract_rules": rules, **fetch_params}
        response = client.html_api(url, params=params)
        response.raise_for_status()
        got = json.loads(response.text)
        values.update({k: v for k, v in got.items() if v is not None})
        missing = [name for name in fields if values.get(name) is None]
        if not missing:  # the next request asks only for missing fields
            break
    return values


def coerce(value, ftype):
    """Read a number field with the same parser as page text."""
    if ftype not in NUMERIC or value is None:
        return value
    found = numbers_in(str(value), ftype)
    return found[0][0] if found else None


def tolerance(value):
    """33900 came from '33.9k', so the true count is in 33850..33949."""
    digits = str(int(value))
    zeros = len(digits) - len(digits.rstrip("0"))
    return 10 ** zeros // 2 if zeros else 0


def matches(got, want, ftype):
    if got is None or want is None:
        return False
    if ftype == "int":
        tol = tolerance(want)
        return got == want or -tol <= got - want < tol
    if ftype == "decimal":
        return got == want  # a price must match to the cent
    return " ".join(str(got).split()) == " ".join(str(want).split())


def css_path(el, root):
    """Shortest selector whose first match is `el`. Stable attributes first."""
    def first_is_el(css):
        try:
            return root.cssselect(css)[:1] == [el]
        except SelectorError:  # an id such as "a:b" is not valid CSS
            return False

    if el.get("id") and not UNSTABLE.search(el.get("id")):
        if first_is_el(f"#{el.get('id')}"):
            return f"#{el.get('id')}"
    for attr in ("itemprop", "data-testid", "data-test", "data-target",
                 "name"):
        css = f'{el.tag}[{attr}="{el.get(attr)}"]'
        if el.get(attr) and first_is_el(css):
            return css
    classes = [c for c in (el.get("class") or "").split()
               if CSS_NAME.fullmatch(c) and not UNSTABLE.search(c)]
    for n in range(1, len(classes) + 1):
        css = el.tag + "".join(f".{c}" for c in classes[:n])
        if first_is_el(css):
            return css
    if el.tag == "script" and el.get("type"):  # JSON-LD has no id or class
        css = f'{el.tag}[type="{el.get("type")}"]'
        if first_is_el(css):
            return css
    parent = el.getparent()
    if parent is None or parent.tag in ("html", "body"):
        return None
    prefix = css_path(parent, root)
    if prefix and first_is_el(f"{prefix} > {el.tag}"):
        return f"{prefix} > {el.tag}"
    return None


def json_leaves(data, path=()):
    if isinstance(data, dict):
        for key, child in data.items():
            yield from json_leaves(child, path + (key,))
    elif isinstance(data, list):
        for i, child in enumerate(data):
            yield from json_leaves(child, path + (i,))
    else:
        yield path, data


def candidates(root, value, ftype):
    """Yield (distance, element, attr, json_path) wherever `value` appears."""
    for script in root.cssselect(JSON_SCRIPTS):
        try:
            payload = json.loads(script.text or "")
        except json.JSONDecodeError:
            continue
        for path, leaf in json_leaves(payload):
            is_int = isinstance(leaf, int) and not isinstance(leaf, bool)
            if ftype == "int" and is_int and matches(leaf, value, "int"):
                yield abs(leaf - value), script, None, list(path)
            elif ftype == "str" and isinstance(leaf, str):
                if matches(leaf, value, "str"):
                    yield 0, script, None, list(path)
            elif ftype == "decimal" and coerce(leaf, ftype) == value:
                yield 0, script, None, list(path)  # 19.99 or "19.99"
    for el in root.iter():
        if not isinstance(el.tag, str) or el.tag in SKIP_TAGS:
            continue
        sources = [(None, el.text)]
        sources += [(a, el.get(a)) for a in VALUE_ATTRS if el.get(a)]
        for attr, raw in sources:
            if ftype in NUMERIC:
                for n, full in numbers_in(raw, ftype):
                    if full and matches(n, value, ftype):
                        yield abs(n - value), el, attr, None
            elif matches(raw, value, "str"):
                yield 0, el, attr, None


def induce_rule(html, value, ftype):
    """Find where `value` appears. Return a rule that reads it exactly."""
    if value is None:
        return None
    root = lxml_html.fromstring(html)
    found = sorted(candidates(root, value, ftype), key=lambda c: c[0])
    for _, el, attr, json_path in found:
        css = css_path(el, root)
        rule = {"css": css, "attr": attr, "type": ftype}
        if json_path is not None:
            rule["json_path"] = json_path
        got = apply_rule(Selector(text=html), rule) if css else None
        if matches(got, value, ftype):
            return rule
    return None


def repair(client, fields, broken, page, holdout):
    """Propose rules for broken fields. Keep the ones a holdout confirms.

    page and holdout are dicts with "url", "html" and "fetch_params".
    """
    want = ai_values(client, page["url"], fields, page["fetch_params"])
    check = ai_values(client, holdout["url"], fields, holdout["fetch_params"])
    promoted, report = {}, {}
    for field in broken:
        ftype = fields[field]["type"]
        value = coerce(want.get(field), ftype)
        expected = coerce(check.get(field), ftype)
        rule = induce_rule(page["html"], value, ftype)
        if rule is None:
            report[field] = f"no exact match on page: {value!r}"
            continue
        got = apply_rule(Selector(text=holdout["html"]), rule)
        if matches(got, expected, ftype):
            promoted[field] = rule
            path = rule.get("json_path") or []
            where = ".".join(map(str, path)) or rule["css"]
            report[field] = f"promoted {where}"
        else:
            report[field] = f"holdout: {got!r} != {expected!r}"
    return promoted, report
