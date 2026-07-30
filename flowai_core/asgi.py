"""
ASGI config for FlowAI.

Exposes the ASGI callable that serves both standard HTTP requests and
WebSocket connections (Django Channels). `websocket_urlpatterns` now pulls
together the monitoring, signals_app, and notifications consumers — routing
was wired here from Phase 1 onward so the protocol split was in place before
any of the individual apps existed.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flowai_core.settings')

# get_asgi_application() must be called before importing anything that
# touches models, so Django's app registry is populated first.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

import monitoring.routing  # noqa: E402
import signals_app.routing  # noqa: E402
import notifications.routing  # noqa: E402
import prediction.routing  # noqa: E402

websocket_urlpatterns = [
    *monitoring.routing.websocket_urlpatterns,
    *signals_app.routing.websocket_urlpatterns,
    *notifications.routing.websocket_urlpatterns,
    *prediction.routing.websocket_urlpatterns,
]

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
