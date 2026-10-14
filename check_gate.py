import os
import re

from scrapingbee import ScrapingBeeClient

from fetch import fetch, fetch_selenium

url = "https://www.walmart.com/ip/5113175776"
title = re.search(r"<title>(.*?)</title>", fetch_selenium(url, "h1"))
print("selenium alone:", title.group(1))

client = ScrapingBeeClient(api_key=os.environ["SCRAPINGBEE_API_KEY"])
target = {"url": url, "anchor": "Chromebook", "wait_css": "h1"}
html, source = fetch(client, target)
title = re.search(r"<title>(.*?)</title>", html).group(1)
print(f"fetch(): {source}, {title[:50]}")
