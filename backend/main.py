import os
import sys
import base64
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add current folder to path to resolve local imports cleanly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_agent import WebAgent
from gemini import GeminiPlanner

app = FastAPI(title="Surfer Backend API")

# Enable CORS for the vanilla client app
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


class GoalRequest(BaseModel):
	goal: str


def execute_agent_goal(goal: str, planner: GeminiPlanner, initial_plan: list[dict]) -> dict:
	executed_history = []
	steps_queue = list(initial_plan)
	max_replan_attempts = 5
	replan_count = 0
	final_screenshot_b64 = ""
	error_message = None

	temp_screenshot = "temp_final_state.png"

	# Run browser with visible window (headed mode by default)
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

				# Record success
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

		# Capture the final browser state as a screenshot
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


@app.post("/run")
def run_agent(payload: GoalRequest):
	if not payload.goal:
		raise HTTPException(status_code=400, detail="Goal prompt cannot be empty.")

	try:
		planner = GeminiPlanner()
		initial_plan = planner.plan(payload.goal)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Planner initialization failed: {e}")

	if not initial_plan:
		raise HTTPException(status_code=422, detail="Failed to generate an initial plan. Check your prompt or API key.")

	# Run automation loop
	result = execute_agent_goal(payload.goal, planner, initial_plan)
	return result


if __name__ == "__main__":
	import uvicorn
	uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
