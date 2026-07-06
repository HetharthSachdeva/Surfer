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
		description="The action type. Must be one of: goto, click, fill, screenshot, get-title, evaluate, stop"
	)
	argument: str = Field(
		default="",
		description="The parameter for the action. For fill, it must be formatted as: selector_or_text|||value. For stop, it is the exit description message."
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
5. If the goal requires private user login (MFA/2FA), credit card input, manual CAPTCHA solving, or credentials you do not have, you must IMMEDIATELY terminate planning. Add a final step: {"action": "stop", "argument": "Human action required: [reason]"}.
6. Keep your plans brief and optimistic.
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
		current_dom: list[dict],
		initial_plan: list[dict],
		screenshot_bytes: bytes = None
	) -> list[dict]:
		"""
		Sends execution history, initial planned path, failure context, current DOM tree, and visual page screenshots
		to Gemini to generate a complete recovery plan to the very end of the user goal.
		"""
		system_instruction = """
You are an expert web automation debugger. An automated web agent encountered an error during task execution.
Review the user's goal, the steps successfully completed so far, the initial plan that was generated, the step that failed, and the error.

You are provided with a visual screenshot of the current page. Visible interactive elements are labeled with red numbered badges.
Analyze both the text DOM elements list and the visual screenshot to choose the best recovery path.

Your task is to generate a BRAND NEW, REVISED execution plan from the current page state ALL THE WAY TO THE VERY END of the user's goal.
Do not stop at just recovering from the immediate error. Plan all subsequent clicks, filters, or cart actions needed to fully accomplish the user's high-level goal.

Rules:
1. To interact with a badged element, you MUST target its number as the argument (e.g. click "4" or fill "2|||value").
2. Prefer using the visual badges in the screenshot to verify element locations and functions.
3. Do not try to repeat the step that failed unless the page state has changed to make it valid.
4. If recovery requires actions that cannot be automated without private inputs (e.g. solving dynamic captchas, logging in, or typing OTP codes), generate a final step: {"action": "stop", "argument": "Human action required: [explain reason]"}.
"""

		prompt = f"""
USER GOAL: {user_goal}

INITIAL PLAN (The plan generated at the start):
{json.dumps(initial_plan, indent=2)}

EXECUTED HISTORY (Steps completed successfully so far):
{json.dumps(executed_history, indent=2)}

FAILED STEP:
{json.dumps(failed_step, indent=2)}

ERROR MESSAGE:
{error_message}

CURRENT PAGE STATE (List of visible interactive elements):
{json.dumps(current_dom, indent=2)}

Generate a new, revised execution plan that starts from the current page state and goes all the way to the end of the user's goal.
"""

		try:
			contents = []
			
			# If screenshot bytes are provided, package them as an image part
			if screenshot_bytes:
				image_part = types.Part.from_bytes(
					data=screenshot_bytes,
					mime_type="image/png"
				)
				contents.append(image_part)
			
			# Append the textual prompt context
			contents.append(prompt)

			response = self.client.models.generate_content(
				model=self.model_name,
				contents=contents,
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
