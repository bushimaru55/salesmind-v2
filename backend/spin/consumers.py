"""
WebSocket consumers for OpenAI Realtime API proxy
"""
import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
import websockets
import os

logger = logging.getLogger(__name__)


class RealtimeConsumer(AsyncWebsocketConsumer):
    """
    OpenAI Realtime API用のWebSocketプロキシ
    クライアント ↔ Django ↔ OpenAI Realtime API
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_ws = None
        self.user = None
        self.session_id = None
        self.forwarding_task = None
        
    async def connect(self):
        """WebSocket接続時の処理"""
        try:
            # クエリパラメータから認証トークンを取得
            query_string = self.scope.get('query_string', b'').decode()
            params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
            token_key = params.get('token')
            
            if not token_key:
                logger.warning("No auth token provided in WebSocket connection")
                await self.close(code=4001)
                return
            
            # ユーザー認証
            self.user = await self.get_user_from_token(token_key)
            if not self.user:
                logger.warning(f"Invalid token: {token_key}")
                await self.close(code=4001)
                return
            
            # セッションIDを取得（オプション）
            self.session_id = params.get('session_id')
            
            logger.info(f"WebSocket connected: user={self.user.username}, session={self.session_id}")
            
            # クライアントとの接続を受け入れ
            await self.accept()
            
            # OpenAI Realtime APIに接続
            await self.connect_to_openai()
            
        except Exception as e:
            logger.error(f"Error in connect: {e}", exc_info=True)
            await self.close(code=4000)
    
    async def disconnect(self, close_code):
        """WebSocket切断時の処理"""
        logger.info(f"WebSocket disconnecting: user={self.user.username if self.user else 'Unknown'}, code={close_code}")
        
        # OpenAI WebSocketを切断
        if self.openai_ws:
            try:
                await self.openai_ws.close()
            except Exception as e:
                logger.error(f"Error closing OpenAI WebSocket: {e}")
        
        # フォワーディングタスクをキャンセル
        if self.forwarding_task:
            self.forwarding_task.cancel()
            try:
                await self.forwarding_task
            except asyncio.CancelledError:
                pass
    
    async def receive(self, text_data=None, bytes_data=None):
        """クライアントからメッセージを受信"""
        try:
            if text_data:
                data = json.loads(text_data)
                logger.debug(f"Received from client: {data.get('type', 'unknown')}")
                
                # OpenAI Realtime APIにメッセージを転送
                if self.openai_ws and self.openai_ws.open:
                    await self.openai_ws.send(text_data)
                else:
                    logger.warning("OpenAI WebSocket not connected")
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'error': {
                            'type': 'connection_error',
                            'message': 'OpenAI Realtime API not connected'
                        }
                    }))
            
            elif bytes_data:
                # バイナリデータ（音声）の場合
                if self.openai_ws and self.openai_ws.open:
                    await self.openai_ws.send(bytes_data)
                    
        except Exception as e:
            logger.error(f"Error in receive: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': {
                    'type': 'server_error',
                    'message': str(e)
                }
            }))
    
    async def connect_to_openai(self):
        """OpenAI Realtime APIに接続"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise Exception("OPENAI_API_KEY not configured")
            
            # OpenAI Realtime API WebSocketエンドポイント
            openai_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            logger.info(f"Connecting to OpenAI Realtime API for user {self.user.username}")
            
            self.openai_ws = await websockets.connect(
                openai_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            
            logger.info(f"Connected to OpenAI Realtime API for user {self.user.username}")
            
            # OpenAIからのメッセージをクライアントに転送するタスクを開始
            self.forwarding_task = asyncio.create_task(self.forward_openai_messages())
            
            # 接続成功をクライアントに通知
            await self.send(text_data=json.dumps({
                'type': 'session.created',
                'session': {
                    'id': self.session_id or 'new',
                    'user': self.user.username
                }
            }))
            
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime API: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': {
                    'type': 'connection_error',
                    'message': f'Failed to connect to OpenAI: {str(e)}'
                }
            }))
            await self.close(code=4002)
    
    async def forward_openai_messages(self):
        """OpenAI Realtime APIからのメッセージをクライアントに転送"""
        try:
            async for message in self.openai_ws:
                if isinstance(message, str):
                    # テキストメッセージ
                    data = json.loads(message)
                    logger.debug(f"Received from OpenAI: {data.get('type', 'unknown')}")
                    await self.send(text_data=message)
                    
                    # セッション履歴に保存（必要に応じて）
                    await self.save_message_to_session(data)
                    
                elif isinstance(message, bytes):
                    # バイナリメッセージ（音声）
                    await self.send(bytes_data=message)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("OpenAI WebSocket connection closed")
        except asyncio.CancelledError:
            logger.info("Forwarding task cancelled")
        except Exception as e:
            logger.error(f"Error in forward_openai_messages: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': {
                    'type': 'forwarding_error',
                    'message': str(e)
                }
            }))
    
    async def save_message_to_session(self, data):
        """メッセージをセッション履歴に保存"""
        try:
            if not self.session_id:
                return
            
            message_type = data.get('type')
            
            # 会話メッセージのみを保存
            if message_type in ['conversation.item.created', 'response.done']:
                await self.save_chat_message(data)
                
        except Exception as e:
            logger.error(f"Error saving message to session: {e}", exc_info=True)
    
    @database_sync_to_async
    def get_user_from_token(self, token_key):
        """トークンからユーザーを取得"""
        try:
            token = Token.objects.select_related('user').get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return None
    
    @database_sync_to_async
    def save_chat_message(self, data):
        """チャットメッセージをデータベースに保存"""
        try:
            from .models import Session, ChatMessage
            
            if not self.session_id:
                return
            
            session = Session.objects.get(id=self.session_id)
            
            # メッセージの内容を抽出
            item = data.get('item', {})
            content = item.get('content', [])
            
            if content:
                # テキストコンテンツを抽出
                text_content = []
                for c in content:
                    if c.get('type') == 'text':
                        text_content.append(c.get('text', ''))
                
                if text_content:
                    message_text = ' '.join(text_content)
                    role = item.get('role', 'assistant')
                    
                    # データベースに保存
                    ChatMessage.objects.create(
                        session=session,
                        role=role,
                        message=message_text
                    )
                    
                    logger.info(f"Saved message to session {self.session_id}: {role}")
                    
        except Exception as e:
            logger.error(f"Error in save_chat_message: {e}", exc_info=True)

