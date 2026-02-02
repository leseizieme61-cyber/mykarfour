from channels.generic.websocket import AsyncJsonWebsocketConsumer

class SlotConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            await self.close()
            return
        # groupe par utilisateur pour ciblage direct
        self.group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # handler appelé lorsque group_send envoie type 'slot.running'
    async def slot_running(self, event):
        # event contient 'slot_id' et 'title'
        await self.send_json({
            'type': 'slot_running',
            'slot_id': event.get('slot_id'),
            'title': event.get('title'),
        })