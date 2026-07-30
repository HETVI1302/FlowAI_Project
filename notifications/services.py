"""
Single entry point for raising a Notification from anywhere in the codebase
(signal optimizer, CV pipeline, prediction module once it exists, etc.).
Persists the row — so the notification center has history and unread counts
survive a page refresh — then broadcasts it to every connected dashboard tab
over the `notifications_broadcast` Channels group. Plain sync function using
the same async_to_sync bridge as monitoring/cv/pipeline.py and
signals_app/optimizer.py, so it's safe to call from a worker process, a
management command, or a request/response view.
"""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .consumers import NOTIFICATIONS_GROUP
from .models import Notification


def notify(category, priority, title, message, intersection=None, recipients=None):
    notification = Notification.objects.create(
        category=category,
        priority=priority,
        title=title,
        message=message,
        intersection=intersection,
    )
    if recipients:
        notification.recipients.set(recipients)

    payload = {
        'type': 'notification.new',
        'id': str(notification.id),
        'category': notification.category,
        'priority': notification.priority,
        'title': notification.title,
        'message': notification.message,
        'intersection_id': str(intersection.id) if intersection else None,
        'intersection_name': intersection.name if intersection else None,
        'created_at': notification.created_at.isoformat(),
        'unread_count': Notification.objects.filter(is_read=False).count(),
    }
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(NOTIFICATIONS_GROUP, {
        'type': 'notification_new',
        'payload': payload,
    })
    return notification
