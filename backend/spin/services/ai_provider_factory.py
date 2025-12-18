"""
AIプロバイダーファクトリー
複数のAIプロバイダー（OpenAI, Claude, Geminiなど）に対応したクライアント生成
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI
import os

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("anthropic library is not installed. Claude API will not be available.")

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    if 'logger' not in locals():
        logger = logging.getLogger(__name__)
    logger.warning("google-generativeai library is not installed. Gemini API will not be available.")

from spin.models import AIProviderKey, AIModel

if 'logger' not in locals():
    logger = logging.getLogger(__name__)


class BaseAIClient(ABC):
    """AIクライアントの基底クラス"""
    
    def __init__(self, provider_key: AIProviderKey):
        self.provider_key = provider_key
        self.client = self._initialize_client()
    
    @abstractmethod
    def _initialize_client(self):
        """クライアントの初期化"""
        pass
    
    @abstractmethod
    def chat_completion(
        self,
        model: AIModel,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """
        チャット補完
        
        Returns:
            Tuple[str, Dict]: (応答テキスト, 使用量情報)
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        接続テスト
        
        Returns:
            Dict: {'success': bool, 'message': str, 'model': str (optional)}
        """
        pass


class OpenAIClient(BaseAIClient):
    """OpenAIクライアント"""
    
    def _initialize_client(self):
        """OpenAIクライアントの初期化"""
        api_key = self.provider_key.api_key
        base_url = self.provider_key.api_endpoint if self.provider_key.api_endpoint else None
        
        return OpenAI(api_key=api_key, base_url=base_url)
    
    def chat_completion(
        self,
        model: AIModel,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """OpenAI チャット補完"""
        try:
            # max_tokensが指定されていない場合、適切なデフォルト値を設定
            # コンテキスト長を超えないように、最大出力トークンを制限
            if max_tokens is None:
                # モデルのコンテキスト長の20-30%程度を出力に割り当て
                context_window = model.context_window or 8192
                max_tokens = min(model.max_output_tokens or 2000, int(context_window * 0.25))
            
            response = self.client.chat.completions.create(
                model=model.model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            content = response.choices[0].message.content
            usage = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens,
            }
            
            return content, usage
        
        except Exception as e:
            logger.error(f"OpenAI chat completion error: {e}")
            raise
    
    def test_connection(self) -> Dict[str, Any]:
        """OpenAI 接続テスト"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # 最も安価なモデルでテスト
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            
            return {
                'success': True,
                'message': f'接続成功（モデル: {response.model}）',
                'model': response.model
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'接続失敗: {str(e)}'
            }


class AnthropicClient(BaseAIClient):
    """Anthropic (Claude) クライアント"""
    
    def _initialize_client(self):
        """Anthropicクライアントの初期化"""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic library is not installed. "
                "Please install it with: pip install anthropic>=0.18.0"
            )
        api_key = self.provider_key.api_key
        return anthropic.Anthropic(api_key=api_key)
    
    def chat_completion(
        self,
        model: AIModel,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """Claude チャット補完"""
        try:
            # Claudeのメッセージフォーマットに変換
            # システムメッセージを分離
            system_message = None
            claude_messages = []
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                else:
                    claude_messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
            
            # Claudeは最初のメッセージがuserである必要がある
            if claude_messages and claude_messages[0]['role'] != 'user':
                claude_messages.insert(0, {'role': 'user', 'content': '...'})
            
            response = self.client.messages.create(
                model=model.model_id,
                max_tokens=max_tokens or model.max_output_tokens or 4096,
                temperature=temperature,
                system=system_message if system_message else anthropic.NOT_GIVEN,
                messages=claude_messages
            )
            
            content = response.content[0].text
            usage = {
                'prompt_tokens': response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens,
                'total_tokens': response.usage.input_tokens + response.usage.output_tokens,
            }
            
            return content, usage
        
        except Exception as e:
            logger.error(f"Anthropic chat completion error: {e}")
            raise
    
    def test_connection(self) -> Dict[str, Any]:
        """Claude 接続テスト"""
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",  # 最も安価なモデルでテスト
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            
            return {
                'success': True,
                'message': f'接続成功（モデル: {response.model}）',
                'model': response.model
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'接続失敗: {str(e)}'
            }


class GoogleClient(BaseAIClient):
    """Google (Gemini) クライアント（将来実装）"""
    
    def _initialize_client(self):
        """Geminiクライアントの初期化"""
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "google-generativeai library is not installed. "
                "Please install it with: pip install google-generativeai"
            )
        # TODO: Google Gemini APIの実装
        raise NotImplementedError("Google Gemini client is not yet implemented")
    
    def chat_completion(
        self,
        model: AIModel,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """Gemini チャット補完"""
        raise NotImplementedError("Google Gemini client is not yet implemented")
    
    def test_connection(self) -> Dict[str, Any]:
        """Gemini 接続テスト"""
        raise NotImplementedError("Google Gemini client is not yet implemented")


class AIProviderFactory:
    """AIプロバイダーのファクトリークラス"""
    
    @staticmethod
    def create_client(provider_key: AIProviderKey) -> BaseAIClient:
        """
        プロバイダーに応じたクライアントを生成
        
        Args:
            provider_key: AIProviderKeyインスタンス
        
        Returns:
            BaseAIClient: プロバイダー固有のクライアント
        
        Raises:
            ValueError: サポートされていないプロバイダーの場合
            ImportError: 必要なライブラリがインストールされていない場合
        """
        if provider_key.provider == 'openai':
            return OpenAIClient(provider_key)
        elif provider_key.provider == 'anthropic':
            if not ANTHROPIC_AVAILABLE:
                raise ImportError(
                    "anthropic library is not installed. "
                    "Please install it with: pip install anthropic>=0.18.0"
                )
            return AnthropicClient(provider_key)
        elif provider_key.provider == 'google':
            if not GOOGLE_AVAILABLE:
                raise ImportError(
                    "google-generativeai library is not installed. "
                    "Please install it with: pip install google-generativeai"
                )
            return GoogleClient(provider_key)
        else:
            raise ValueError(f"Unsupported provider: {provider_key.provider}")
    
    @staticmethod
    def get_client_and_model_for_purpose(purpose: str) -> Tuple[Optional[BaseAIClient], Optional[AIModel]]:
        """
        用途に応じたクライアントとモデルを取得
        
        Args:
            purpose: 用途（'spin_generation', 'chat', 'scoring', 'scraping_analysis'）
        
        Returns:
            Tuple[BaseAIClient, AIModel]: クライアントとモデルのタプル
        
        Raises:
            ValueError: 設定が見つからない場合
        """
        from spin.models import ModelConfiguration
        
        try:
            config = ModelConfiguration.objects.get(purpose=purpose, is_active=True)
        except ModelConfiguration.DoesNotExist:
            logger.error(f"No active ModelConfiguration found for purpose: {purpose}")
            return None, None
        
        # プライマリを試行
        provider_key, model = config.get_provider_and_model()
        
        if provider_key and model:
            try:
                client = AIProviderFactory.create_client(provider_key)
                logger.info(f"Using primary provider for {purpose}: {provider_key.provider} / {model.model_id}")
                return client, model
            except Exception as e:
                logger.warning(f"Primary provider failed for {purpose}: {e}")
        
        # フォールバックを試行
        if config.has_fallback():
            fallback_provider_key, fallback_model = config.get_fallback_provider_and_model()
            if fallback_provider_key and fallback_model:
                try:
                    client = AIProviderFactory.create_client(fallback_provider_key)
                    logger.info(f"Using fallback provider for {purpose}: {fallback_provider_key.provider} / {fallback_model.model_id}")
                    return client, fallback_model  # fallback_modelを返す
                except Exception as e:
                    logger.error(f"Fallback provider also failed for {purpose}: {e}")
        
        logger.error(f"No available provider for purpose: {purpose}")
        return None, None

