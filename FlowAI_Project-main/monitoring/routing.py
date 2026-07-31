from django.urls import re_path

from . import consumers

# Included from flowai_core/asgi.py into the project-wide websocket_urlpatterns.
websocket_urlpatterns = [
    re_path(r'^ws/monitoring/overview/$', consumers.MonitoringOverviewConsumer.as_asgi()),
    re_path(
        r'^ws/monitoring/(?P<intersection_id>[0-9a-f-]{36})/$',
        consumers.MonitoringIntersectionConsumer.as_asgi(),
    ),
]
