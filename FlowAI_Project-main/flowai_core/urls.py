"""
Root URL configuration for FlowAI.
App-specific urls.py files are added as each module is built out.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .views import landing_page

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing_page, name='home'),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('app/', include('dashboard.urls', namespace='dashboard')),
    path('app/monitoring/', include('monitoring.urls', namespace='monitoring')),
    path('app/signals/', include('signals_app.urls', namespace='signals_app')),
    path('app/notifications/', include('notifications.urls', namespace='notifications')),
    path('app/prediction/', include('prediction.urls', namespace='prediction')),
    path('app/analytics/', include('analytics.urls', namespace='analytics')),
    path('app/reports/', include('reports.urls', namespace='reports')),
    # path('api/', include('api.urls')),   # added when the api app is built
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
