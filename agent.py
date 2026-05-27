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
from web_agent import WebAgent


def run_task(url: str, task: str, input_str: str | None, headless: bool = False, timeout: int = 60000):
	with WebAgent(headless=headless, timeout=timeout) as agent:
		agent.navigate(url)

		try:
			if task == "get-title":
				out = agent.get_title()

			elif task == "screenshot":
				filename = input_str or "screenshot.png"
				agent.screenshot(filename)
				out = f"screenshot saved: {filename}"

			elif task == "get-text":
				if not input_str:
					raise ValueError("get-text requires a selector as input")
				out = agent.get_text(input_str)

			elif task == "click":
				if not input_str:
					raise ValueError("click requires a selector as input")
				agent.click(input_str)
				out = f"clicked {input_str}"

			elif task == "fill":
				if not input_str or "|||" not in input_str:
					raise ValueError("fill requires input in the form selector|||value")
				selector, value = input_str.split("|||", 1)
				agent.fill(selector, value)
				out = f"filled {selector}"

			elif task == "evaluate":
				if not input_str:
					raise ValueError("evaluate requires a JS expression as input")
				out = agent.evaluate(input_str)

			else:
				out = f"unknown task: {task}"

		except Exception as e:
			out = f"error: {e}"

		print(out)


def main():
	parser = argparse.ArgumentParser(description="Simple Playwright CLI runner")
	parser.add_argument("url", help="URL to open")
	parser.add_argument("task", help="Task to perform (get-title, get-text, click, fill, screenshot, evaluate)")
	parser.add_argument("input", nargs="?", help="Optional input for the task")
	parser.add_argument("--headless", dest="headless", action="store_true", help="Run browser in headless mode")
	parser.add_argument("--headed", dest="headless", action="store_false", help="Run browser with a visible window")
	parser.add_argument("--timeout", type=int, default=60000, help="Timeout in ms for navigation and actions (default 60000)")

	parser.set_defaults(headless=False)
	args = parser.parse_args()

	run_task(args.url, args.task, args.input, headless=args.headless, timeout=args.timeout)


if __name__ == "__main__":
	main()

