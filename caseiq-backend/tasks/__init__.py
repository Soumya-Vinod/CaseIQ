# This makes sure all task modules are imported when Celery starts
from .celery import app as celery_app
from . import embedding_tasks
from . import pdf_tasks

__all__ = ("celery_app",)