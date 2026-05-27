#!/usr/bin/env python3
"""
Simple Playwright Runner from tasks.txt

Configure your task in tasks.txt (line-by-line):
Line 1: URL to load
Line 2: Task to perform
Line 3: Optional input for the task
"""

import os
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
	if not os.path.exists("tasks.txt"):
		print("Error: tasks.txt not found. Please create it.")
		sys.exit(1)

	with open("tasks.txt", "r", encoding="utf-8") as f:
		lines = [line.strip() for line in f if line.strip()]

	if len(lines) < 2:
		print("Error: tasks.txt must contain at least a URL (Line 1) and a task (Line 2).")
		sys.exit(1)

	url = lines[0]
	task = lines[1]
	input_str = lines[2] if len(lines) > 2 else None

	# Run browser with visible window (headless=False)
	run_task(url, task, input_str, headless=False)


if __name__ == "__main__":
	main()
