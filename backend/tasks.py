import os
import sys
import base64
import redis
import json
from celery_app import celery_app

# Add current folder to path to resolve local imports cleanly inside workers
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_agent import WebAgent
from gemini import GeminiPlanner

# Synchronous Redis client for publishing logs and state updates
redis_client = redis.Redis(host="localhost", port=6379, db=0)


def publish_update(task_id: str, status: str, log_message: str, history: list, screenshot_b64: str = None):
	"""
	Publishes raw execution progress, thought logs, and browser screenshots
	to the corresponding task channel on Redis Pub/Sub.
	"""
	payload = {
		"status": status,
		"log": log_message,
		"history": history,
		"screenshot": screenshot_b64
	}
	redis_client.publish(f"task:{task_id}", json.dumps(payload))


@celery_app.task(bind=True, name="tasks.run_agent_task")
def run_agent_task(self, goal: str, initial_plan: list[dict]) -> dict:
	"""
	Celery background task that executes the agent browser loop and returns 
	the completed step logs and base64 screenshot.
	"""
	task_id = self.request.id
	
	# Publish initial start message
	publish_update(task_id, "processing", "Task initiated. Initializing planner...", [])

	# Instantiate planner inside worker context
	planner = GeminiPlanner()
	
	executed_history = []
	steps_queue = list(initial_plan)
	max_replan_attempts = 5
	replan_count = 0
	final_screenshot_b64 = ""
	error_message = None
	temp_screenshot = f"temp_final_state_{task_id}.png"

	# Launch Playwright in headless=True mode, streaming captures to client
	with WebAgent(headless=True, timeout=45000) as agent:
		while steps_queue and replan_count < max_replan_attempts:
			# Check if user requested cancellation via Redis flag
			if redis_client.get(f"cancelled:{task_id}"):
				error_message = "Task cancelled by user request."
				break

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

				elif task == "stop":
					# Human action required / terminal stop state
					error_message = input_str
					out = f"Agent stopped: {input_str}"
					step_with_result = {**step, "result": out, "status": "success"}
					executed_history.append(step_with_result)
					steps_queue.pop(0)
					break

				else:
					out = f"Unknown task: {task}"

				# Record success in task history logs
				step_with_result = {**step, "result": out, "status": "success"}
				executed_history.append(step_with_result)
				steps_queue.pop(0)

				# Capture intermediate clean screenshot (no badges) and stream update to user
				screenshot_b64 = None
				try:
					agent.screenshot(temp_screenshot)
					if os.path.exists(temp_screenshot):
						with open(temp_screenshot, "rb") as image_file:
							screenshot_b64 = base64.b64encode(image_file.read()).decode("utf-8")
						os.remove(temp_screenshot)
				except Exception as sc_err:
					print(f"Failed to capture progress screenshot: {sc_err}")

				publish_update(task_id, "processing", out, executed_history, screenshot_b64)

			except Exception as e:
				# Log failure internally
				step_with_result = {**step, "result": str(e), "status": "failed"}
				executed_history.append(step_with_result)
				
				replan_count += 1
				print(f"Error executing step {step}: {e}. Re-planning attempt {replan_count}...")
				
				# 1. Capture clean screenshot of raw failure state for the user
				failure_screenshot_b64 = None
				try:
					agent.screenshot(temp_screenshot)
					if os.path.exists(temp_screenshot):
						with open(temp_screenshot, "rb") as image_file:
							failure_screenshot_b64 = base64.b64encode(image_file.read()).decode("utf-8")
						os.remove(temp_screenshot)
				except Exception as sc_err:
					print(f"Failed to capture clean failure screenshot: {sc_err}")

				# 2. Publish step failed log along with clean screenshot to the user
				publish_update(task_id, "processing", f"Step failed: {step.get('action')}. Attempting recovery replan...", executed_history, failure_screenshot_b64)

				# 3. Now apply the visual overlays solely for Gemini Vision
				try:
					current_dom = agent.get_interactive_elements()
					agent.apply_set_of_mark()
				except Exception as dom_err:
					error_message = f"Failed to parse active DOM during error recovery: {dom_err}"
					break

				# 4. Capture the screenshot WITH badges for Gemini API
				screenshot_bytes = None
				try:
					agent.screenshot(temp_screenshot)
					if os.path.exists(temp_screenshot):
						with open(temp_screenshot, "rb") as f:
							screenshot_bytes = f.read()
						os.remove(temp_screenshot)
				except Exception as sc_err:
					print(f"Failed to capture error page screenshot for Gemini Vision: {sc_err}")

				# 5. Clear markers immediately so they don't block clicks in the next actions
				try:
					agent.clear_set_of_mark()
				except Exception:
					pass

				# 6. Ask Gemini to re-route plan, sending DOM, original plan, and badged screenshot bytes
				new_plan = planner.replan(
					user_goal=goal,
					executed_history=executed_history,
					failed_step=step,
					error_message=str(e),
					current_dom=current_dom,
					initial_plan=initial_plan,
					screenshot_bytes=screenshot_bytes
				)

				if not new_plan:
					error_message = f"Replanner returned empty recovery plan after step failed: {e}"
					break

				steps_queue = list(new_plan)
				publish_update(task_id, "processing", "New recovery route planned by Gemini.", executed_history)

		# Capture final state of the page (clean, no badges)
		try:
			agent.screenshot(temp_screenshot)
			if os.path.exists(temp_screenshot):
				with open(temp_screenshot, "rb") as image_file:
					final_screenshot_b64 = base64.b64encode(image_file.read()).decode("utf-8")
				os.remove(temp_screenshot)
		except Exception as sc_err:
			print(f"Failed to capture final screenshot: {sc_err}")

	# Broadcast final outcomes to the user
	is_success = len(steps_queue) == 0 and not error_message
	final_status = "success" if is_success else "failed"
	final_log = "Goal accomplished successfully!" if is_success else f"Task aborted: {error_message}"
	publish_update(task_id, final_status, final_log, executed_history, final_screenshot_b64)

	return {
		"history": executed_history,
		"screenshot": final_screenshot_b64,
		"success": is_success,
		"error": error_message
	}
