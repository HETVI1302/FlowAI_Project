from channels.generic.websocket import AsyncJsonWebsocketConsumer

# One broadcast group for every connected operator — notifications are a
# city-wide concern (accident on one intersection matters to everyone
# watching the dashboard), not scoped per-intersection like monitoring.
NOTIFICATIONS_GROUP = 'notifications_broadcast'


class NotificationsConsumer(AsyncJsonWebsocketConsumer):
    """
    ws/notifications/ — a single, project-wide feed. Loaded from base.html
    (see static/js/notifications.js) for every authenticated page, not just
    the notification center, so the nav bell and toasts stay live no matter
    where the operator is in the app.
    """

    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close(code=4001)
            return
        await self.channel_layer.group_add(NOTIFICATIONS_GROUP, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection.ack', 'group': NOTIFICATIONS_GROUP})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(NOTIFICATIONS_GROUP, self.channel_name)

    async def notification_new(self, event):
        await self.send_json(event['payload'])
