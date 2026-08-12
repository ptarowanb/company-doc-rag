import os

from celery import Celery  # type: ignore[import-untyped]

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("company_doc_rag", broker=redis_url, backend=redis_url)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
