# Makes sure the Celery app is loaded whenever Django starts (not just
# when `celery -A config worker` runs it directly), so `@shared_task`
# decorators elsewhere in the project always find a configured app.
from .celery import app as celery_app

__all__ = ("celery_app",)
