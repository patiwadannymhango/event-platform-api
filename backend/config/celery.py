import os

from celery import Celery

# Same pattern Django's own docs use for wiring Celery into a project —
# the worker process (`celery -A config worker`) imports this module, so
# it needs DJANGO_SETTINGS_MODULE set before anything touches
# `django.conf.settings`. Defaults to development like manage.py/wsgi.py/
# asgi.py do — production sets the real env var (see backend/.env on the
# server), this is only the local-dev fallback.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("config")

# Reads every CELERY_* setting from Django's settings (CELERY_BROKER_URL
# etc. in config/settings/base.py) rather than a separate config file.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Finds tasks.py in every installed app automatically (e.g.
# apps/notifications/tasks.py) — new task modules need no extra wiring
# here.
app.autodiscover_tasks()
