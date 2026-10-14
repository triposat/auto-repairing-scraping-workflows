from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


def fetch_selenium(url, wait_css):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_css)))
        except TimeoutException:
            pass  # the content check in fetch() decides what this page is
        return driver.page_source
    finally:
        driver.quit()


def fetch(client, target):
    """Selenium first. If it is not the requested page, use ScrapingBee."""
    html = fetch_selenium(target["url"], target["wait_css"])
    if target["anchor"] in html:
        return html, "selenium"
    params = dict(target.get("escalate_params", {"mode": "auto"}))
    response = client.html_api(target["url"], params=params)
    if response.ok and target["anchor"] in response.text:
        return response.text, "scrapingbee"
    raise RuntimeError(f"anchor not found: {target['url']}")
