from django.urls import path

from . import views

app_name = 'signals_app'

urlpatterns = [
    path('', views.control_panel, name='control_panel'),
    path('<uuid:signal_id>/override/', views.manual_override, name='manual_override'),
    path('<uuid:signal_id>/set-dynamic/', views.set_dynamic_mode, name='set_dynamic_mode'),
]
