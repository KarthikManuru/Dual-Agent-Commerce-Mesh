"""
Standalone RQ Worker process for asynchronous, durable webhook event execution.
Run as: python -m app.workers.run_worker
"""
import sys
import os
import redis
from rq import Worker, Queue, Connection
from app.config import get_settings

settings = get_settings()

listen = ["webhook_events"]

if __name__ == "__main__":
    print(f"[RQ Worker] Connecting to Redis at {settings.REDIS_URL}...")
    try:
        conn = redis.from_url(settings.REDIS_URL)
        with Connection(conn):
            worker = Worker(map(Queue, listen))
            print(f"[RQ Worker] Listening on queues: {listen}. Ready for webhook events.")
            worker.work(with_scheduler=True)
    except Exception as e:
        print(f"[RQ Worker] Fatal error: {e}")
        sys.exit(1)
