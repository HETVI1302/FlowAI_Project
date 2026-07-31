import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer

# ---------------------------------------------------------------------------
# Group naming — the CV worker (monitoring/cv/pipeline.py) publishes here via
# `channel_layer.group_send`, and every dashboard/monitoring browser tab that
# is currently looking at that intersection (or the city-wide overview) joins
# the matching group on connect. Consumers do no DB or CV work themselves —
# they only relay group messages to their socket, keeping the WebSocket layer
# thin per the architecture requirement (async work stays in the worker).
# ---------------------------------------------------------------------------

OVERVIEW_GROUP = 'monitoring_overview'


def intersection_group_name(intersection_id):
    return f'monitoring_intersection_{intersection_id}'


class MonitoringOverviewConsumer(AsyncJsonWebsocketConsumer):
    """
    ws/monitoring/overview/ — city-wide feed used by the live Dashboard:
    every intersection's vehicle counts, congestion level, and emergency
    flags in one stream, so the dashboard cards update without polling.
    """

    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close(code=4001)
            return
        await self.channel_layer.group_add(OVERVIEW_GROUP, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection.ack', 'group': OVERVIEW_GROUP})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(OVERVIEW_GROUP, self.channel_name)

    # Handler name must match the "type" key (dots -> underscores) used in
    # group_send() calls from the CV worker / signal optimizer / notifications.
    async def monitoring_update(self, event):
        await self.send_json(event['payload'])

    async def emergency_alert(self, event):
        await self.send_json(event['payload'])


class MonitoringIntersectionConsumer(AsyncJsonWebsocketConsumer):
    """
    ws/monitoring/<intersection_id>/ — detail feed for a single
    intersection's monitoring page: per-camera vehicle counts, bounding
    boxes for the live overlay, queue length, and waiting time.
    """

    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close(code=4001)
            return
        self.intersection_id = self.scope['url_route']['kwargs']['intersection_id']
        self.group_name = intersection_group_name(self.intersection_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection.ack', 'group': self.group_name})

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def monitoring_update(self, event):
        await self.send_json(event['payload'])

    async def emergency_alert(self, event):
        await self.send_json(event['payload'])

    # Allows a browser tab to request the camera to reconnect / re-heartbeat,
    # e.g. after the operator clicks "retry feed" on an offline camera tile.
    async def receive_json(self, content, **kwargs):
        if content.get('action') == 'ping':
            await self.send_json({'type': 'pong'})
