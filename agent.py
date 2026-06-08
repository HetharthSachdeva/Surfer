#!/usr/bin/env python3
"""
Surfer LLM Operator - Playwright Agent

Accepts natural language user goals via terminal input, compiles them into 
actionable web steps using Gemini, and executes them in a headed browser window.
"""

import sys
from web_agent import WebAgent
from gemini import GeminiPlanner


def run_sequence(instructions: list[dict], headless: bool = False, timeout: int = 60000):
	if not instructions:
		print("\n❌ No instructions were generated. Aborting.")
		return

	print("\n🚀 Executing Plan:")
	with WebAgent(headless=headless, timeout=timeout) as agent:
		for idx, step in enumerate(instructions, 1):
			task = step.get("action", "").strip().lower()
			input_str = step.get("argument", "").strip()

			print(f"\n[{idx}/{len(instructions)}] Action: {task} {input_str or ''}")

			try:
				if task == "goto":
					if not input_str:
						raise ValueError("goto requires a URL as input")
					agent.navigate(input_str)
					out = f"Navigated to {input_str}"

				elif task == "get-title":
					out = f"Title: {agent.get_title()}"

				elif task == "screenshot":
					filename = input_str or "screenshot.png"
					agent.screenshot(filename)
					out = f"Screenshot saved: {filename}"

				elif task == "get-text":
					if not input_str:
						raise ValueError("get-text requires a selector as input")
					out = f"Text found: {agent.get_text(input_str)}"

				elif task == "click":
					if not input_str:
						raise ValueError("click requires a selector as input")
					agent.click(input_str)
					out = f"Clicked {input_str}"

				elif task == "fill":
					if not input_str or "|||" not in input_str:
						raise ValueError("fill requires input in the form selector|||value")
					selector, value = input_str.split("|||", 1)
					agent.fill(selector, value)
					out = f"Filled {selector}"

				elif task == "evaluate":
					if not input_str:
						raise ValueError("evaluate requires a JS expression as input")
					out = agent.evaluate(input_str)

				else:
					out = f"Unknown task: {task}"

			except Exception as e:
				out = f"Error: {e}"
				print(f"↳ {out}")
				print("\n❌ Flow execution aborted due to error.")
				break

			print(f"↳ {out}")
	print("\n✨ Done!")


def main():
	print("=" * 60)
	print("🤖 Welcome to Surfer - Your AI Web Operator 🤖")
	print("=" * 60)

	try:
		goal = input("\nWhat would you like me to do today?\n> ").strip()
	except KeyboardInterrupt:
		print("\nGoodbye!")
		sys.exit(0)

	if not goal:
		print("Goal cannot be empty. Exiting.")
		sys.exit(1)

	print("\n🧠 Consulting Gemini for the execution plan...")
	try:
		planner = GeminiPlanner()
		plan = planner.plan(goal)
	except Exception as err:
		print(f"\n❌ Planner Initialization Error: {err}")
		sys.exit(1)

	if not plan:
		print("Failed to generate a plan. Please check your prompt or your .env API key.")
		sys.exit(1)

	print("\n📋 Generated Action Plan:")
	for idx, step in enumerate(plan, 1):
		print(f"  {idx}. {step.get('action')}: {step.get('argument')}")

	# Keep headed mode as default so user can watch the browser live
	run_sequence(plan, headless=False, timeout=45000)


if __name__ == "__main__":
	main()
