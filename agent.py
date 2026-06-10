#!/usr/bin/env python3
"""
Surfer LLM Operator - Playwright Agent

Accepts natural language user goals via terminal input, compiles them into 
actionable web steps using Gemini, and executes them in a headed browser window.
"""

import sys
from web_agent import WebAgent
from gemini import GeminiPlanner


def run_with_replanning(goal: str, initial_plan: list[dict], planner: GeminiPlanner, headless: bool = False, timeout: int = 60000):
	if not initial_plan:
		print("\n❌ No initial instructions were generated. Aborting.")
		return

	print("\n🚀 Executing Plan:")
	
	executed_history = []
	steps_queue = list(initial_plan)
	max_replan_attempts = 5
	replan_count = 0

	with WebAgent(headless=headless, timeout=timeout) as agent:
		while steps_queue and replan_count < max_replan_attempts:
			step = steps_queue[0]
			task = step.get("action", "").strip().lower()
			input_str = step.get("argument", "").strip()

			print(f"\n⚡ Action: {task} {input_str or ''}")

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
						raise ValueError("get-text requires a selector or index as input")
					out = f"Text found: {agent.get_text(input_str)}"

				elif task == "click":
					if not input_str:
						raise ValueError("click requires a selector or index as input")
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

				print(f"↳ Success: {out}")
				executed_history.append(step)
				steps_queue.pop(0)  # Remove completed step from the queue

			except Exception as e:
				print(f"↳ ⚠️ Error encountered: {e}")
				replan_count += 1
				print(f"🔄 Attempting Reactive Re-planning (Attempt {replan_count}/{max_replan_attempts})...")

				# Extract current page DOM elements safely
				try:
					current_dom = agent.get_interactive_elements()
				except Exception as dom_err:
					print(f"❌ Failed to extract DOM elements from active page: {dom_err}")
					break

				# Ask Gemini for a new recovery plan
				new_plan = planner.replan(
					user_goal=goal,
					executed_history=executed_history,
					failed_step=step,
					error_message=str(e),
					current_dom=current_dom
				)

				if not new_plan:
					print("❌ Replanner failed to generate a recovery plan. Aborting.")
					break

				print("\n📋 Dynamic Recovery Plan Generated:")
				for idx, r_step in enumerate(new_plan, 1):
					print(f"  {idx}. {r_step.get('action')}: {r_step.get('argument')}")

				# Overwrite the remaining queue with the new steps
				steps_queue = list(new_plan)

	if not steps_queue:
		print("\n✨ Goal successfully achieved!")
	else:
		print("\n❌ Failed to achieve goal (max replan attempts reached or replan failed).")


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
	run_with_replanning(goal, plan, planner, headless=False, timeout=45000)


if __name__ == "__main__":
	main()
