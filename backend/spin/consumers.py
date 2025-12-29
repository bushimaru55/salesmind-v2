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
        # 会話履歴用のバッファ
        self.pending_user_transcript = None  # ユーザーの発言を一時保存
        self.message_sequence = 0  # メッセージの順番を管理
        
    async def connect(self):
        """WebSocket接続時の処理"""
        try:
            logger.info("=" * 80)
            logger.info("WebSocket接続リクエスト受信")
            
            # クエリパラメータから認証トークンを取得
            query_string = self.scope.get('query_string', b'').decode()
            logger.info(f"Query string: {query_string[:100]}...")  # 最初の100文字のみ
            
            params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
            token_key = params.get('token')
            
            if not token_key:
                logger.error("❌ 認証トークンが提供されていません")
                await self.close(code=4001)
                return
            
            logger.info(f"トークン確認: {token_key[:10]}...")
            
            # ユーザー認証
            self.user = await self.get_user_from_token(token_key)
            if not self.user:
                logger.error(f"❌ 無効なトークン: {token_key[:10]}...")
                await self.close(code=4001)
                return
            
            # セッションIDを取得（オプション）
            self.session_id = params.get('session_id')
            
            logger.info(f"✅ WebSocket接続受け入れ: user={self.user.username}, session={self.session_id}")
            
            # セッションをrealtime_mode=Trueに更新し、既存のメッセージ数を取得
            if self.session_id:
                await self.update_session_realtime_mode(True)
                self.message_sequence = await self.get_message_count()
                logger.info(f"📊 既存メッセージ数: {self.message_sequence}")
            
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
        
        # セッションをrealtime_mode=Falseに更新
        if self.session_id:
            await self.update_session_realtime_mode(False)
        
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
                logger.info(f"📨 クライアントからテキスト受信: type={data.get('type', 'unknown')}")
                logger.debug(f"メッセージ内容: {text_data[:200]}...")
                
                # OpenAI Realtime APIにメッセージを転送
                if self.openai_ws:
                    try:
                        await self.openai_ws.send(text_data)
                        logger.info(f"✅ OpenAIへテキスト転送成功")
                    except Exception as e:
                        logger.error(f"❌ OpenAIへのテキスト送信失敗: {e}", exc_info=True)
                        await self.send(text_data=json.dumps({
                            'type': 'error',
                            'error': {
                                'type': 'connection_error',
                                'message': 'OpenAI Realtime API not connected'
                            }
                        }))
                else:
                    logger.warning("⚠️ OpenAI WebSocket未接続")
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'error': {
                            'type': 'connection_error',
                            'message': 'OpenAI Realtime API not connected'
                        }
                    }))
            
            elif bytes_data:
                # バイナリデータ（音声）の場合
                # OpenAI Realtime APIはJSON形式のinput_audio_buffer.appendイベントを期待
                bytes_len = len(bytes_data)
                logger.debug(f"🎤 クライアントから音声データ受信: {bytes_len} bytes")
                
                if self.openai_ws:
                    try:
                        # PCM16バイナリをBase64エンコードしてJSON形式で送信
                        import base64
                        audio_base64 = base64.b64encode(bytes_data).decode('utf-8')
                        audio_event = {
                            "type": "input_audio_buffer.append",
                            "audio": audio_base64
                        }
                        await self.openai_ws.send(json.dumps(audio_event))
                        logger.debug(f"✅ OpenAIへ音声転送成功: {bytes_len} bytes (Base64)")
                    except Exception as e:
                        logger.error(f"❌ OpenAIへの音声送信失敗: {e}", exc_info=True)
                    
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
            logger.info("-" * 80)
            logger.info("OpenAI Realtime API接続開始")
            
            # Django管理画面から登録されたAPIキーを取得
            api_key = await self.get_openai_api_key()
            if not api_key:
                logger.error("❌ OpenAI APIキーが設定されていません")
                raise Exception("OPENAI_API_KEY not configured")
            
            logger.info(f"APIキー取得成功: {api_key[:10]}...{api_key[-4:]}")
            
            # OpenAI Realtime API WebSocketエンドポイント（GA版）
            openai_url = "wss://api.openai.com/v1/realtime?model=gpt-realtime"
            
            # websocketsライブラリのバージョンに応じてヘッダーを設定
            headers = [
                ("Authorization", f"Bearer {api_key[:10]}..."),
                ("OpenAI-Beta", "realtime=v1")
            ]
            
            logger.info(f"接続先URL: {openai_url}")
            logger.info(f"ユーザー: {self.user.username}")
            logger.info("WebSocket接続試行中...")
            
            self.openai_ws = await websockets.connect(
                openai_url,
                additional_headers=[
                    ("Authorization", f"Bearer {api_key}"),
                    ("OpenAI-Beta", "realtime=v1")
                ],
                ping_interval=20,
                ping_timeout=10
            )
            
            logger.info(f"✅ OpenAI Realtime API接続成功 (user={self.user.username})")
            logger.info(f"WebSocket state: {self.openai_ws.state}")
            
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
            logger.info("📡 OpenAIメッセージ転送タスク開始")
            
            async for message in self.openai_ws:
                if isinstance(message, str):
                    # テキストメッセージ
                    data = json.loads(message)
                    msg_type = data.get('type', 'unknown')
                    logger.info(f"📩 OpenAIからメッセージ受信: type={msg_type}")
                    
                    # エラーメッセージは詳細ログ
                    if msg_type == 'error':
                        logger.error(f"❌ OpenAIエラー: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    else:
                        logger.debug(f"メッセージ内容: {message[:300]}...")
                    
                    await self.send(text_data=message)
                    logger.debug(f"✅ クライアントへ転送完了")
                    
                    # セッション履歴に保存（必要に応じて）
                    await self.save_message_to_session(data)
                    
                elif isinstance(message, bytes):
                    # バイナリメッセージ（音声）
                    logger.debug(f"🔊 OpenAIから音声受信: {len(message)} bytes")
                    await self.send(bytes_data=message)
                    logger.debug(f"✅ クライアントへ音声転送完了")
                    
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
            
            # OpenAI Realtime APIの主要なイベントタイプを処理
            
            # ユーザーの発言（音声トランスクリプト完了）
            if message_type == 'conversation.item.input_audio_transcription.completed':
                transcript = data.get('transcript', '')
                if transcript and transcript.strip():
                    logger.info(f"💬 ユーザー発言を保存: {transcript[:50]}...")
                    await self.save_chat_message_direct(
                        role='salesperson',
                        message=transcript.strip()
                    )
            
            # AIの応答（トランスクリプト完了）
            elif message_type == 'response.audio_transcript.done':
                transcript = data.get('transcript', '')
                if transcript and transcript.strip():
                    logger.info(f"🤖 AI応答を保存: {transcript[:50]}...")
                    await self.save_chat_message_direct(
                        role='customer',
                        message=transcript.strip()
                    )
            
            # フォールバック: response.output_item.done も処理
            elif message_type == 'response.output_item.done':
                item = data.get('item', {})
                if item.get('role') == 'assistant':
                    content = item.get('content', [])
                    for c in content:
                        if c.get('type') == 'audio' and c.get('transcript'):
                            transcript = c.get('transcript', '')
                            if transcript and transcript.strip():
                                # response.audio_transcript.doneで既に保存されている可能性があるのでスキップ
                                # logger.debug(f"response.output_item.done: {transcript[:50]}...")
                                pass
                
        except Exception as e:
            logger.error(f"Error saving message to session: {e}", exc_info=True)
    
    @database_sync_to_async
    def update_session_realtime_mode(self, is_realtime):
        """セッションのリアルタイムモードを更新"""
        try:
            from .models import Session
            session = Session.objects.get(id=self.session_id, user=self.user)
            session.realtime_mode = is_realtime
            session.save(update_fields=['realtime_mode'])
            logger.info(f"✅ Session {self.session_id} realtime_mode updated to {is_realtime}")
        except Session.DoesNotExist:
            logger.warning(f"⚠️ Session {self.session_id} not found for user {self.user.username}")
        except Exception as e:
            logger.error(f"❌ Failed to update session realtime_mode: {e}", exc_info=True)
    
    @database_sync_to_async
    def get_message_count(self):
        """セッションの既存メッセージ数を取得"""
        try:
            from .models import Session
            session = Session.objects.get(id=self.session_id, user=self.user)
            return session.messages.count()
        except Session.DoesNotExist:
            return 0
        except Exception as e:
            logger.error(f"Error getting message count: {e}")
            return 0
    
    @database_sync_to_async
    def get_user_from_token(self, token_key):
        """トークンからユーザーを取得"""
        try:
            token = Token.objects.select_related('user').get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_openai_api_key(self):
        """Django管理画面から登録されたOpenAI APIキーを取得"""
        try:
            from .models import AIProviderKey
            
            # AIProviderKeyテーブルからOpenAI APIキーを取得
            # 優先順位: 1) デフォルトキー, 2) 最初の有効なキー
            api_key_obj = AIProviderKey.objects.filter(
                provider='openai',
                is_active=True
            ).order_by('-is_default', '-created_at').first()
            
            if api_key_obj:
                logger.info(f"OpenAI APIキーを取得しました: {api_key_obj.name}")
                return api_key_obj.api_key
            else:
                logger.error("OpenAI APIキーが見つかりません。Django管理画面（API統合管理）から登録してください。")
                return None
            
        except Exception as e:
            logger.error(f"APIキー取得エラー: {e}", exc_info=True)
            return None
    
    @database_sync_to_async
    def save_chat_message(self, data):
        """チャットメッセージをデータベースに保存（レガシー）"""
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
                    elif c.get('type') == 'audio' and c.get('transcript'):
                        text_content.append(c.get('transcript', ''))
                
                if text_content:
                    message_text = ' '.join(text_content)
                    role = item.get('role', 'assistant')
                    
                    # ロール変換: OpenAI形式 -> SalesMind形式
                    db_role = 'customer' if role == 'assistant' else 'salesperson'
                    
                    # シーケンス番号を取得
                    self.message_sequence += 1
                    
                    # データベースに保存
                    ChatMessage.objects.create(
                        session=session,
                        role=db_role,
                        message=message_text,
                        sequence=self.message_sequence
                    )
                    
                    logger.info(f"Saved message to session {self.session_id}: {db_role} (seq={self.message_sequence})")
                    
        except Exception as e:
            logger.error(f"Error in save_chat_message: {e}", exc_info=True)
    
    @database_sync_to_async
    def save_chat_message_direct(self, role: str, message: str):
        """チャットメッセージを直接データベースに保存"""
        try:
            from .models import Session, ChatMessage
            
            if not self.session_id:
                logger.warning("save_chat_message_direct: session_id is None")
                return
            
            session = Session.objects.get(id=self.session_id)
            
            # シーケンス番号を取得（既存のメッセージ数+1）
            existing_count = session.messages.count()
            sequence = existing_count + 1
            
            # データベースに保存
            ChatMessage.objects.create(
                session=session,
                role=role,
                message=message,
                sequence=sequence
            )
            
            logger.info(f"✅ Saved {role} message to session {self.session_id} (seq={sequence}): {message[:30]}...")
                
        except Session.DoesNotExist:
            logger.error(f"Session not found: {self.session_id}")
        except Exception as e:
            logger.error(f"Error in save_chat_message_direct: {e}", exc_info=True)

