# Auto-repairing scraping workflow with Selenium and ScrapingBee

[![Monthly test](https://github.com/triposat/auto-repairing-scraping-workflows/actions/workflows/monthly-test.yml/badge.svg)](https://github.com/triposat/auto-repairing-scraping-workflows/actions/workflows/monthly-test.yml)

A Selenium scraper that repairs its own broken selectors. Code for the ScrapingBee article "Building Auto-Repairing Scraping Workflows with AutoQALLMs and Selenium".

## How it works

1. Selenium fetches the page. If the site blocks Selenium, ScrapingBee fetches it instead.
2. Each field is checked against its expected type and format.
3. For a broken field, ScrapingBee's AI extraction reads the correct value, and the code builds a CSS or JSON-path rule that returns it.
4. The new rule is saved only if it also works on a second page with the same layout. Otherwise the field goes to `needs_review.json`.

## Quick start

You need Python 3.10 or later, Google Chrome, and a [ScrapingBee API key](https://app.scrapingbee.com/account/register).

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export SCRAPINGBEE_API_KEY="YOUR-API-KEY"
python run.py
```

On Windows PowerShell, set the key with `$env:SCRAPINGBEE_API_KEY="YOUR-API-KEY"`.

`rules.json` starts with rules written for GitHub's 2019 page layout. The first run repairs them and saves the new rules. Run it again, and it uses the saved rules with no AI calls. `example-output.txt` shows both runs.

To start over from the 2019 rules:

```bash
cp rules.v1.json rules.json
cp last_good.v1.json last_good.json
```

## More examples

| Command | What it does |
|---|---|
| `python check_strict.py` | Returns `None` for "16.5k" instead of a rounded number, and keeps the cents in "$1,299.99". No API key needed. |
| `python check_gate.py` | Fetches a Walmart product page with Selenium, then with the ScrapingBee fallback. |
| `python run_books.py` | Fixes a broken price rule shared by 20 pages, with 1 repair instead of 20. |

## Fix the rules with a coding agent

This part also needs [Claude Code](https://code.claude.com/docs/en/overview).

```bash
python save_fixtures.py           # save the 2 test pages (once, uses API credits)
cp rules.v1.json rules.json       # start from the 2019 rules
python verify.py                  # prints FAIL
cp mcp.json.example ../mcp.json   # then add your API key to ../mcp.json
bash agent.sh
python verify.py                  # prints PASS
```

`agent.sh` lets Claude Code read this folder, edit `rules.json`, run `verify.py`, and call 2 ScrapingBee MCP tools, and nothing else. `mcp.json` goes one folder up, so the agent can't read your key.

## Files

| File | Contents |
|---|---|
| `autorepair.py` | Rule format, extraction, strict parsing, and validation |
| `fetch.py` | Selenium fetch with the ScrapingBee fallback |
| `repair.py` | Rule building from AI extraction values, and the check on a second page |
| `batch.py` | One repair per template for a batch of pages |
| `spot_check.py` | Audit of saved rules against AI extraction on a random sample |
| `run.py` | The GitHub example |

A [GitHub Actions workflow](.github/workflows/monthly-test.yml) runs the examples against the live pages on the 1st of each month.

## License

MIT
