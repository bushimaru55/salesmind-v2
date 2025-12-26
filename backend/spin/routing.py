"""
WebSocket URL routing for Django Channels
"""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/realtime/', consumers.RealtimeConsumer.as_asgi()),
]

