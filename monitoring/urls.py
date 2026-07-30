from django.urls import path

from . import views

app_name = 'monitoring'

urlpatterns = [
    path('', views.live_monitoring, name='live'),
    path('<uuid:intersection_id>/', views.intersection_detail, name='detail'),
]
