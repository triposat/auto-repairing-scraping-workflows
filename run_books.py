import json
import os
from pathlib import Path

import requests
from parsel import Selector
from scrapingbee import ScrapingBeeClient

from batch import run_batch

FIELDS = {
    "title": {"type": "str",
              "description": "the book title in the main heading"},
    "price": {"type": "decimal",
              "description": "the book price shown under the title"},
}
base = "https://books.toscrape.com/catalogue/"
catalog = requests.get(base + "page-1.html", timeout=30).text
links = Selector(text=catalog).css("h3 a::attr(href)").getall()
pages = [{"url": base + link, "anchor": "Product Information",
          "wait_css": "h1", "fetch_params": {"render_js": False}}
         for link in links]

# A separate rules file keeps the GitHub rules unchanged.
rules = Path("books_rules.json")
rules.write_text(json.dumps({"version": 1, "history": [], "rules": {
    "title": {"xpath": "//div[contains(@class, 'product_main')]/h1",
              "attr": None, "type": "str"},
    "price": {"css": "p.price-now", "attr": None, "type": "decimal"},
}}, indent=2))

client = ScrapingBeeClient(api_key=os.environ["SCRAPINGBEE_API_KEY"])
run_batch(client, pages, FIELDS, rules_path=rules)
