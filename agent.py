#!/usr/bin/env python3
"""
Modular Playwright Flow Runner

Configure your flow in tasks.txt:
- Lines starting with '#' can be comments or settings (e.g. '# headless: False')
- All other lines are steps in the format: <action> [parameter]
"""

import os
import sys
from web_agent import WebAgent


def run_sequence(instructions: list[str], headless: bool = False, timeout: int = 60000):
	if not instructions:
		print("No instructions to execute.")
		return

	with WebAgent(headless=headless, timeout=timeout) as agent:
		for idx, line in enumerate(instructions, 1):
			parts = line.split(maxsplit=1)
			task = parts[0].strip().lower()
			input_str = parts[1].strip() if len(parts) > 1 else None

			print(f"\n[{idx}/{len(instructions)}] Executing: {task} {input_str or ''}")

			try:
				if task == "goto":
					if not input_str:
						raise ValueError("goto requires a URL as input")
					agent.navigate(input_str)
					out = f"navigated to {input_str}"

				elif task == "get-title":
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
				print(f"Result: {out}")
				print("Aborting flow execution due to error.")
				break

			print(f"Result: {out}")


def main():
	if not os.path.exists("tasks.txt"):
		print("Error: tasks.txt not found. Please create it.")
		sys.exit(1)

	headless = False
	timeout = 60000
	instructions = []

	with open("tasks.txt", "r", encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			if line.startswith("#"):
				# Parse optional settings from comments, e.g., "# headless: True"
				if ":" in line:
					key, val = line[1:].split(":", 1)
					key = key.strip().lower()
					val = val.strip()
					if key == "headless":
						headless = val.lower() in ("true", "1", "yes")
					elif key == "timeout":
						try:
							timeout = int(val)
						except ValueError:
							pass
				continue
			instructions.append(line)

	run_sequence(instructions, headless=headless, timeout=timeout)


if __name__ == "__main__":
	main()
