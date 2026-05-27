#!/usr/bin/env python3
"""
Simple Playwright CLI runner

Usage examples:
  python agent.py https://example.com get-title
  python agent.py https://example.com get-text "h1"
  python agent.py https://example.com screenshot screenshot.png
  python agent.py https://example.com fill "#name|||Alice"

Tasks supported:
- get-title: prints the page title
- get-text: prints inner text of a selector (input = selector)
- click: clicks a selector (input = selector)
- fill: fills a selector with value (input = selector|||value)
- screenshot: saves a screenshot (input = filename)
- evaluate: runs JS expression and prints result (input = js)

Note: Install browsers with `playwright install` after installing the `playwright` package.
"""

import argparse
import json
import sys
from playwright.sync_api import sync_playwright


def run_task(url: str, task: str, input_str: str | None, headless: bool = False, timeout: int = 60000):
	with sync_playwright() as p:
		browser = p.chromium.launch(headless=headless, slow_mo=500)
		page = browser.new_page()
		page.set_default_timeout(timeout)
		page.goto(url)

		try:
			if task == "get-title":
				out = page.title()

			elif task == "screenshot":
				filename = input_str or "screenshot.png"
				page.screenshot(path=filename, full_page=True)
				out = f"screenshot saved: {filename}"

			elif task == "get-text":
				if not input_str:
					raise ValueError("get-text requires a selector as input")
				locator = page.locator(input_str)
				out = locator.inner_text()

			elif task == "click":
				if not input_str:
					raise ValueError("click requires a selector as input")
				page.click(input_str)
				out = f"clicked {input_str}"

			elif task == "fill":
				if not input_str or "|||" not in input_str:
					raise ValueError("fill requires input in the form selector|||value")
				selector, value = input_str.split("|||", 1)
				page.fill(selector, value)
				out = f"filled {selector}"

			elif task == "evaluate":
				if not input_str:
					raise ValueError("evaluate requires a JS expression as input")
				val = page.evaluate(input_str)
				try:
					out = json.dumps(val, ensure_ascii=False)
				except Exception:
					out = str(val)

			else:
				out = f"unknown task: {task}"

		except Exception as e:
			out = f"error: {e}"

		finally:
			browser.close()

		print(out)


def main():
	parser = argparse.ArgumentParser(description="Simple Playwright CLI runner")
	parser.add_argument("url", help="URL to open")
	parser.add_argument("task", help="Task to perform (get-title, get-text, click, fill, screenshot, evaluate)")
	parser.add_argument("input", nargs="?", help="Optional input for the task")
	parser.add_argument("--headless", dest="headless", action="store_true", help="Run browser in headless mode")
	parser.add_argument("--headed", dest="headless", action="store_false", help="Run browser with a visible window")
	parser.add_argument("--timeout", type=int, default=60000, help="Timeout in ms for navigation and actions (default 60000)")

	parser.set_defaults(headless=True)
	args = parser.parse_args()

	run_task(args.url, args.task, args.input, headless=args.headless, timeout=args.timeout)


if __name__ == "__main__":
	main()

