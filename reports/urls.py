from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.report_list, name='list'),
    path('request/', views.request_report, name='request'),
    path('<uuid:report_id>/download/', views.download_report, name='download'),
]
