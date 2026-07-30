from channels.generic.websocket import AsyncJsonWebsocketConsumer

# ---------------------------------------------------------------------------
# Same shape as monitoring/consumers.py: the optimizer (signals_app/optimizer.py)
# and the emergency-priority hook publish here via `channel_layer.group_send`;
# this consumer only relays group messages to the socket. One city-wide group
# is enough for the control panel — per-signal channels aren't needed since
# operators watch the whole grid, not one intersection at a time.
# ---------------------------------------------------------------------------

SIGNALS_GROUP = 'signals_overview'


class SignalsOverviewConsumer(AsyncJsonWebsocketConsumer):
    """
    ws/signals/overview/ — powers the Signal Management control panel:
    live timing changes (AI-optimized or manual) and emergency-priority
    overrides, so operators see the effect of the optimizer without
    refreshing.
    """

    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close(code=4001)
            return
        await self.channel_layer.group_add(SIGNALS_GROUP, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection.ack', 'group': SIGNALS_GROUP})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(SIGNALS_GROUP, self.channel_name)

    # Handler name must match the "type" key (dots -> underscores) used in
    # group_send() calls from optimizer.py.
    async def signal_update(self, event):
        await self.send_json(event['payload'])

    async def emergency_priority(self, event):
        await self.send_json(event['payload'])
