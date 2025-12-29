"""
ASGI config for salesmind project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "salesmind.settings")

# Django ASGIアプリケーションを初期化（HTTP用）
django_asgi_app = get_asgi_application()

# WebSocketルーティングをインポート
from spin.routing import websocket_urlpatterns

# プロトコル別にルーティング
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
