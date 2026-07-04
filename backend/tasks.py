import os
import sys
import base64
from celery_app import celery_app

# Add current folder to path to resolve local imports cleanly inside workers
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_agent import WebAgent
from gemini import GeminiPlanner


@celery_app.task(name="tasks.run_agent_task")
def run_agent_task(goal: str, initial_plan: list[dict]) -> dict:
	"""
	Celery background task that executes the agent browser loop and returns 
	the completed step logs and base64 screenshot.
	"""
	# Instantiate planner inside worker context
	planner = GeminiPlanner()
	
	executed_history = []
	steps_queue = list(initial_plan)
	max_replan_attempts = 5
	replan_count = 0
	final_screenshot_b64 = ""
	error_message = None

	temp_screenshot = f"temp_final_state_{run_agent_task.request.id}.png"

	# Launch Playwright in headless=False mode so user can see browser actions live
	with WebAgent(headless=False, timeout=45000) as agent:
		while steps_queue and replan_count < max_replan_attempts:
			step = steps_queue[0]
			task = step.get("action", "").strip().lower()
			input_str = step.get("argument", "").strip()

			try:
				if task == "goto":
					if not input_str:
						raise ValueError("goto requires a URL as input")
					agent.navigate(input_str)
					out = f"Navigated to {input_str}"

				elif task == "get-title":
					out = f"Title: {agent.get_title()}"

				elif task == "screenshot":
					filename = input_str or temp_screenshot
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

				# Record success in task history logs
				step_with_result = {**step, "result": out, "status": "success"}
				executed_history.append(step_with_result)
				steps_queue.pop(0)

			except Exception as e:
				# Log failure internally
				step_with_result = {**step, "result": str(e), "status": "failed"}
				executed_history.append(step_with_result)
				
				replan_count += 1
				print(f"Error executing step {step}: {e}. Re-planning attempt {replan_count}...")

				try:
					current_dom = agent.get_interactive_elements()
				except Exception as dom_err:
					error_message = f"Failed to parse active DOM during error recovery: {dom_err}"
					break

				# Ask Gemini to re-route plan
				new_plan = planner.replan(
					user_goal=goal,
					executed_history=executed_history,
					failed_step=step,
					error_message=str(e),
					current_dom=current_dom
				)

				if not new_plan:
					error_message = f"Replanner returned empty recovery plan after step failed: {e}"
					break

				steps_queue = list(new_plan)

		# Capture final state of the page
		try:
			agent.screenshot(temp_screenshot)
			if os.path.exists(temp_screenshot):
				with open(temp_screenshot, "rb") as image_file:
					final_screenshot_b64 = base64.b64encode(image_file.read()).decode("utf-8")
				os.remove(temp_screenshot)
		except Exception as sc_err:
			print(f"Failed to capture final screenshot: {sc_err}")

	return {
		"history": executed_history,
		"screenshot": final_screenshot_b64,
		"success": len(steps_queue) == 0,
		"error": error_message
	}
