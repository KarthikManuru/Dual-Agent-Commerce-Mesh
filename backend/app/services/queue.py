import asyncio
import redis
from rq import Queue
from app.config import get_settings

settings = get_settings()

try:
    redis_conn = redis.from_url(settings.REDIS_URL)
    webhook_queue = Queue("webhook_events", connection=redis_conn)
except Exception:
    redis_conn = None
    webhook_queue = None


def enqueue_webhook_event(event_id: str, event_type: str, payload: dict):
    """
    Enqueue a webhook event:
    1. If Redis is available, enqueue to RQ 'webhook_events' queue for durable job tracking.
    2. Also trigger async processing task directly in the event loop for instant real-time response.
    """
    from app.workers.webhook_worker import process_webhook_event_task, process_webhook_event_async

    if webhook_queue:
        try:
            webhook_queue.enqueue(
                process_webhook_event_task,
                event_id,
                event_type,
                payload,
                job_timeout=60,
            )
        except Exception as e:
            print(f"[Queue] RQ enqueue error: {e}")

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(process_webhook_event_async(event_id, event_type, payload))
    except RuntimeError:
        # If no running loop in current thread, execute in a new loop
        try:
            asyncio.run(process_webhook_event_async(event_id, event_type, payload))
        except Exception as e:
            print(f"[Queue] Direct async execution error: {e}")
