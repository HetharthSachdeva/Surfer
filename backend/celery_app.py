from celery import Celery

# Initialize Celery app routing tasks and results through local Redis database 0
celery_app = Celery(
	"surfer_tasks",
	broker="redis://localhost:6379/0",
	backend="redis://localhost:6379/0"
)

# Optional configuration settings
celery_app.conf.update(
	task_track_started=True,
	task_serializer="json",
	result_serializer="json",
	accept_content=["json"],
	timezone="UTC",
	enable_utc=True,
	broker_transport_options={"protocol": 2},          # Forces RESP2 (Redis 5 compatibility)
	result_backend_transport_options={"protocol": 2},   # Forces RESP2 (Redis 5 compatibility)
)
