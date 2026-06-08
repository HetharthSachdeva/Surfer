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
1. Prefer using semantic text matching (e.g. "Login", "Sign In") for click and fill tasks over complex CSS/XPath selectors.
2. For the fill action, format the argument exactly as: <selector_or_text>|||<value>.
3. For screenshot, provide a filename as the argument.
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
