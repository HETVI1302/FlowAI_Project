"""
WSGI config for FlowAI.
Kept alongside asgi.py for tooling that expects a WSGI callable
(e.g. some management commands / static-only deployments). The real
runtime path in production is ASGI via Daphne/Uvicorn — see asgi.py.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flowai_core.settings')

application = get_wsgi_application()
