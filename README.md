# Playwright CLI runner

A tiny CLI that uses Playwright (Python) to perform simple tasks against a URL and print a result.

Install:

```bash
python -m pip install -r requirements.txt
python -m playwright install
```

Usage:

```bash
python agent.py <url> <task> [input] [--headed|--headless] [--timeout <ms>]
```

Examples:

```bash
python agent.py https://example.com get-title
python agent.py https://example.com get-text "h1"
python agent.py https://example.com screenshot screenshot.png
python agent.py https://example.com fill "#name|||Alice"
python agent.py https://example.com evaluate "() => document.title"
```

Tasks supported:

- `get-title`: prints the page title
- `get-text`: prints inner text of a selector (input = selector)
- `click`: clicks a selector (input = selector)
- `fill`: fills a selector with value (input = selector|||value)
- `screenshot`: saves a screenshot (input = filename)
- `evaluate`: runs a JS expression and prints the result (input = JS)

Notes:

- After `pip install`, run `python -m playwright install` to download browser binaries.
- Use the `--headed` flag to run with a visible browser window.
