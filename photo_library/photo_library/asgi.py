import os
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import shared_photo_library.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'photo_library.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            shared_photo_library.routing.websocket_urlpatterns
        )
    ),
})