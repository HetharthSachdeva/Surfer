import os
import sys
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from celery.result import AsyncResult
import redis
import redis.asyncio as aioredis

# Connect to local Redis 0
redis_client = redis.Redis(host="localhost", port=6379, db=0)

# Add current folder to path to resolve local imports cleanly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gemini import GeminiPlanner
from celery_app import celery_app
from tasks import run_agent_task

app = FastAPI(title="Surfer Backend API")

# Enable CORS for the client frontend
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


class GoalRequest(BaseModel):
	goal: str


@app.post("/run")
def run_agent(payload: GoalRequest):
	"""
	Submits the goal to the Gemini planner and triggers the Playwright sequence 
	asynchronously inside a background Celery worker, returning a Task ID instantly.
	"""
	if not payload.goal:
		raise HTTPException(status_code=400, detail="Goal prompt cannot be empty.")

	try:
		planner = GeminiPlanner()
		initial_plan = planner.plan(payload.goal)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Planner initialization failed: {e}")

	if not initial_plan:
		raise HTTPException(status_code=422, detail="Failed to generate an initial plan. Check your prompt or API key.")

	# Dispatch execution loop to the background Celery worker queue
	task = run_agent_task.delay(payload.goal, initial_plan)
	
	return {
		"task_id": task.id,
		"status": "pending"
	}


@app.post("/stop/{task_id}")
def stop_task(task_id: str):
	"""
	Sets a cancellation flag in Redis for the given task ID.
	The Celery worker loops check this flag and abort execution immediately.
	"""
	# Set key with a TTL of 300 seconds (5 minutes)
	redis_client.set(f"cancelled:{task_id}", "true", ex=300)
	return {"status": "stop_requested"}


@app.get("/status/{task_id}")
def get_task_status(task_id: str):
	"""
	Polls the database/broker to check the state of the background browser task.
	"""
	task_result = AsyncResult(task_id, app=celery_app)

	if task_result.state == "PENDING":
		return {"status": "pending"}
	elif task_result.state == "STARTED" or task_result.state == "RETRY":
		return {"status": "processing"}
	elif task_result.state == "SUCCESS":
		# Result is fully available
		return {
			"status": "success",
			"result": task_result.result
		}
	elif task_result.state == "FAILURE":
		return {
			"status": "failed",
			"error": str(task_result.info)
		}
	
	return {"status": task_result.state.lower()}


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
	"""
	Establishes WebSocket channel to stream execution frames and logs 
	published by the worker to Redis Pub/Sub in real-time.
	"""
	await websocket.accept()

	# Connect to local Redis 0 asynchronously
	redis_client = aioredis.from_url("redis://localhost:6379/0")
	pubsub = redis_client.pubsub()
	
	# Subscribe to the specific task execution channel
	channel_name = f"task:{task_id}"
	await pubsub.subscribe(channel_name)

	try:
		# Stream inbound Redis events down the open WebSocket connection
		async for message in pubsub.listen():
			if message["type"] == "message":
				data = message["data"].decode("utf-8")
				await websocket.send_text(data)
	except WebSocketDisconnect:
		print(f"Client disconnected from WebSocket stream for task: {task_id}")
	except Exception as e:
		print(f"Error in WebSocket task stream {task_id}: {e}")
	finally:
		# Clean up connections on socket close
		await pubsub.unsubscribe(channel_name)
		await redis_client.close()


if __name__ == "__main__":
	import uvicorn
	uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
