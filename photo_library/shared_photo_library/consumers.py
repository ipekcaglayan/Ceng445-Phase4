from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
import json
from .models import *
from datetime import datetime
from django.db.models import Q
from isbnlib import meta


class NotificationConsumer(WebsocketConsumer):
    def connect(self):
        self.room_name = "notification"
        self.room_group_name = 'notification'

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)
        print(text_data)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'notification_handler',
                'data': data
            }
        )

    def notification_handler(self, event):
        print(event)
        # Send message to WebSocket
        self.send(text_data=json.dumps(event['data']))

