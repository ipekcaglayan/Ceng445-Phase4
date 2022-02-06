from . import consumers
from django.urls import path, re_path


websocket_urlpatterns = [
    re_path(r'^notification/$', consumers.NotificationConsumer.as_asgi()),
]
