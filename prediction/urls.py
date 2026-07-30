from django.urls import path

from . import views

app_name = 'prediction'

urlpatterns = [
    path('', views.forecast, name='forecast'),
    path('<uuid:incident_id>/resolve/', views.resolve_incident, name='resolve_incident'),
]
