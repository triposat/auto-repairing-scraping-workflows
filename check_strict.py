from parsel import Selector

from autorepair import apply_rule

html = '<a class="social-count js-social-count">16.5k</a>'
rule = {"css": "a.js-social-count", "attr": None, "type": "int"}
print(apply_rule(Selector(text=html), rule))

html = '<p class="price">Now $1,299.99</p>'
rule = {"xpath": "//p[@class='price']", "attr": None, "type": "decimal"}
print(apply_rule(Selector(text=html), rule))
