import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Load environment variables from .env
load_dotenv()


class AutomationStep(BaseModel):
	action: str = Field(
		description="The action type. Must be one of: goto, click, fill, screenshot, get-title, evaluate"
	)
	argument: str = Field(
		default="",
		description="The parameter for the action. For fill, it must be formatted as: selector_or_text|||value. For screenshot, it is the filename."
	)


class ExecutionPlan(BaseModel):
	steps: list[AutomationStep] = Field(description="The list of sequential steps to execute.")


class GeminiPlanner:
	def __init__(self, model_name: str = "gemini-2.5-flash"):
		self.api_key = os.getenv("GEMINI_API_KEY")
		if not self.api_key:
			raise ValueError("GEMINI_API_KEY is not set. Please add it to your .env file.")
		
		# Initialize official google-genai client
		self.client = genai.Client(api_key=self.api_key)
		self.model_name = model_name

	def plan(self, user_goal: str) -> list[dict]:
		"""
		Sends the high-level user goal to Gemini and returns a guaranteed list of 
		structured step dictionaries.
		"""
		system_instruction = """
You are a web automation planner. Your job is to translate a user's high-level goal into a sequence of clean browser steps.
Analyze the user's request and plan a path.

Rules:
1. Plan the steps logically starting with navigating to a target website.
2. For the click action, the argument must be the selector or semantic text (e.g. "Login", "Sign In").
3. For the fill action, format the argument exactly as: <selector_or_text>|||<value>.
4. For screenshot, provide a filename as the argument.
5. Keep your plans brief and optimistic.
"""

		try:
			response = self.client.models.generate_content(
				model=self.model_name,
				contents=user_goal,
				config=types.GenerateContentConfig(
					system_instruction=system_instruction,
					temperature=0.1,  # Low temperature for deterministic planning
					response_mime_type="application/json",
					response_schema=ExecutionPlan,  # Force structured Pydantic response
				)
			)

			# Parse output safely as JSON
			plan_data = json.loads(response.text)
			return plan_data.get("steps", [])

		except Exception as e:
			print(f"Error communicating with Gemini Planner: {e}")
			return []

	def replan(
		self, 
		user_goal: str, 
		executed_history: list[dict], 
		failed_step: dict, 
		error_message: str, 
		current_dom: list[dict]
	) -> list[dict]:
		"""
		Sends execution history, failure context, and active DOM state to Gemini
		to generate a dynamic recovery plan.
		"""
		system_instruction = """
You are an expert web automation debugger. An automated web agent encountered an error during task execution.
Review the user's goal, the steps successfully completed so far, the step that failed, and the error.
Look at the visible elements currently on the page and generate a brand-new plan of steps to complete the user's goal from the current state.

Rules:
1. Look closely at the list of visible elements under CURRENT PAGE STATE. 
2. To interact with an element, you MUST target it by its "index" number in the argument (e.g. click "4" or fill "2|||value").
3. Do not try to repeat the step that failed unless the page state has changed to make it valid.
"""

		prompt = f"""
USER GOAL: {user_goal}

EXECUTED HISTORY (Steps completed successfully):
{json.dumps(executed_history, indent=2)}

FAILED STEP:
{json.dumps(failed_step, indent=2)}

ERROR MESSAGE:
{error_message}

CURRENT PAGE STATE (List of visible interactive elements):
{json.dumps(current_dom, indent=2)}

Generate a new, revised execution plan to complete the user's goal from this state.
"""

		try:
			response = self.client.models.generate_content(
				model=self.model_name,
				contents=prompt,
				config=types.GenerateContentConfig(
					system_instruction=system_instruction,
					temperature=0.1,
					response_mime_type="application/json",
					response_schema=ExecutionPlan,
				)
			)

			plan_data = json.loads(response.text)
			return plan_data.get("steps", [])

		except Exception as e:
			print(f"Error communicating with Gemini Replanner: {e}")
			return []
