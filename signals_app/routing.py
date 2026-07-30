from django.urls import re_path

from . import consumers

# Included from flowai_core/asgi.py into the project-wide websocket_urlpatterns.
websocket_urlpatterns = [
    re_path(r'^ws/signals/overview/$', consumers.SignalsOverviewConsumer.as_asgi()),
]
