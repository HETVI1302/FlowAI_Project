from channels.generic.websocket import AsyncJsonWebsocketConsumer

# Same shape as monitoring/consumers.py and signals_app/consumers.py:
# prediction/services.py publishes here, this consumer only relays.
PREDICTION_GROUP = 'prediction_overview'


class PredictionOverviewConsumer(AsyncJsonWebsocketConsumer):
    """
    ws/prediction/overview/ — powers the Predictions page: rolling
    congestion forecasts per intersection and incident/anomaly alerts as
    the engine (run_prediction_engine) raises them.
    """

    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close(code=4001)
            return
        await self.channel_layer.group_add(PREDICTION_GROUP, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection.ack', 'group': PREDICTION_GROUP})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(PREDICTION_GROUP, self.channel_name)

    async def forecast_update(self, event):
        await self.send_json(event['payload'])

    async def incident_alert(self, event):
        await self.send_json(event['payload'])
