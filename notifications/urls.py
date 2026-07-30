from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.center, name='center'),
    path('unread-count/', views.unread_count, name='unread_count'),
    path('<uuid:notification_id>/read/', views.mark_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
]
