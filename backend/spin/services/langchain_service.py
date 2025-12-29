"""
LangChain統合サービス
複数のAIプロバイダーをLangChainで統一的に管理
"""
import logging
from typing import Optional, Dict, Any, List, Tuple, Generator
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

# プロバイダー別のインポート（遅延読み込み）
_OPENAI_AVAILABLE = False
_ANTHROPIC_AVAILABLE = False

try:
    from langchain_openai import ChatOpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("langchain-openai is not installed. OpenAI will not be available via LangChain.")

try:
    from langchain_anthropic import ChatAnthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    logger.warning("langchain-anthropic is not installed. Anthropic will not be available via LangChain.")


class LangChainService:
    """LangChainを使用したAIサービス"""
    
    def __init__(self):
        self._chat_models: Dict[str, BaseChatModel] = {}
    
    def get_chat_model(
        self,
        provider_key,
        model,
        temperature: float = 0.7,
        streaming: bool = False,
    ) -> BaseChatModel:
        """
        プロバイダーとモデルに応じたChatModelを取得
        
        Args:
            provider_key: AIProviderKeyインスタンス
            model: AIModelインスタンス
            temperature: Temperature設定
            streaming: ストリーミングを有効化
        
        Returns:
            BaseChatModel: LangChain ChatModelインスタンス
        """
        cache_key = f"{provider_key.id}_{model.id}_{temperature}_{streaming}"
        
        if cache_key in self._chat_models:
            return self._chat_models[cache_key]
        
        chat_model = self._create_chat_model(provider_key, model, temperature, streaming)
        self._chat_models[cache_key] = chat_model
        return chat_model
    
    def _create_chat_model(
        self,
        provider_key,
        model,
        temperature: float,
        streaming: bool,
    ) -> BaseChatModel:
        """ChatModelを作成"""
        provider = provider_key.provider
        
        if provider == 'openai':
            if not _OPENAI_AVAILABLE:
                raise ImportError(
                    "langchain-openai is not installed. "
                    "Please install it with: pip install langchain-openai"
                )
            return ChatOpenAI(
                api_key=provider_key.api_key,
                model=model.model_id,
                temperature=temperature,
                max_tokens=model.max_output_tokens or 2000,
                streaming=streaming,
            )
        
        elif provider == 'anthropic':
            if not _ANTHROPIC_AVAILABLE:
                raise ImportError(
                    "langchain-anthropic is not installed. "
                    "Please install it with: pip install langchain-anthropic"
                )
            return ChatAnthropic(
                api_key=provider_key.api_key,
                model=model.model_id,
                temperature=temperature,
                max_tokens=model.max_output_tokens or 4096,
                streaming=streaming,
            )
        
        else:
            raise ValueError(f"Unsupported provider for LangChain: {provider}")
    
    def chat_completion(
        self,
        provider_key,
        model,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        チャット補完を実行
        
        Args:
            provider_key: AIProviderKeyインスタンス
            model: AIModelインスタンス
            messages: メッセージリスト [{"role": "user", "content": "..."}]
            temperature: Temperature設定
            max_tokens: 最大トークン数
        
        Returns:
            Tuple[str, Dict]: (応答テキスト, 使用量情報)
        """
        chat_model = self.get_chat_model(provider_key, model, temperature, streaming=False)
        
        # メッセージをLangChain形式に変換
        langchain_messages = self._convert_messages(messages)
        
        # 呼び出し
        response = chat_model.invoke(langchain_messages)
        
        # 使用量情報を抽出
        usage = {}
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata
            if 'token_usage' in metadata:
                token_usage = metadata['token_usage']
                usage = {
                    'prompt_tokens': token_usage.get('prompt_tokens', 0),
                    'completion_tokens': token_usage.get('completion_tokens', 0),
                    'total_tokens': token_usage.get('total_tokens', 0),
                }
            elif 'usage' in metadata:
                # Anthropic形式
                usage_data = metadata['usage']
                usage = {
                    'prompt_tokens': usage_data.get('input_tokens', 0),
                    'completion_tokens': usage_data.get('output_tokens', 0),
                    'total_tokens': usage_data.get('input_tokens', 0) + usage_data.get('output_tokens', 0),
                }
        
        return response.content, usage
    
    def chat_completion_stream(
        self,
        provider_key,
        model,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """
        ストリーミングでチャット補完を実行
        
        Yields:
            str: 応答テキストのチャンク
        """
        chat_model = self.get_chat_model(provider_key, model, temperature, streaming=True)
        
        # メッセージをLangChain形式に変換
        langchain_messages = self._convert_messages(messages)
        
        # ストリーミング呼び出し
        for chunk in chat_model.stream(langchain_messages):
            if chunk.content:
                yield chunk.content
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[BaseMessage]:
        """辞書形式のメッセージをLangChain形式に変換"""
        langchain_messages = []
        
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'system':
                langchain_messages.append(SystemMessage(content=content))
            elif role == 'user':
                langchain_messages.append(HumanMessage(content=content))
            elif role == 'assistant':
                langchain_messages.append(AIMessage(content=content))
            else:
                # 不明なロールはuserとして扱う
                langchain_messages.append(HumanMessage(content=content))
        
        return langchain_messages
    
    def count_tokens(self, text: str, model_name: str = "gpt-4") -> int:
        """
        テキストのトークン数をカウント
        
        Args:
            text: カウント対象のテキスト
            model_name: モデル名（エンコーディング選択用）
        
        Returns:
            int: トークン数
        """
        try:
            import tiktoken
            
            # モデル名からエンコーディングを取得
            try:
                encoding = tiktoken.encoding_for_model(model_name)
            except KeyError:
                # 不明なモデルの場合はcl100k_baseを使用
                encoding = tiktoken.get_encoding("cl100k_base")
            
            return len(encoding.encode(text))
        except ImportError:
            # tiktokenがない場合は文字数/4で概算
            return len(text) // 4
    
    def count_messages_tokens(
        self,
        messages: List[Dict[str, str]],
        model_name: str = "gpt-4"
    ) -> int:
        """
        メッセージリストの合計トークン数をカウント
        
        Args:
            messages: メッセージリスト
            model_name: モデル名
        
        Returns:
            int: 合計トークン数
        """
        total = 0
        for msg in messages:
            content = msg.get('content', '')
            total += self.count_tokens(content, model_name)
            # メッセージのメタデータ用に追加トークンを加算
            total += 4  # role等のオーバーヘッド
        
        return total + 3  # 会話全体のオーバーヘッド
    
    def test_connection(self, provider_key, model) -> Dict[str, Any]:
        """
        接続テストを実行
        
        Returns:
            Dict: {'success': bool, 'message': str}
        """
        try:
            chat_model = self._create_chat_model(provider_key, model, temperature=0.7, streaming=False)
            
            # 簡単なテストメッセージを送信
            response = chat_model.invoke([HumanMessage(content="Hello")])
            
            return {
                'success': True,
                'message': f'接続成功（モデル: {model.model_id}）',
                'model': model.model_id,
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'接続失敗: {str(e)}',
            }
    
    def clear_cache(self):
        """キャッシュされたChatModelをクリア"""
        self._chat_models.clear()


# シングルトンインスタンス
_langchain_service: Optional[LangChainService] = None


def get_langchain_service() -> LangChainService:
    """LangChainサービスのシングルトンインスタンスを取得"""
    global _langchain_service
    if _langchain_service is None:
        _langchain_service = LangChainService()
    return _langchain_service


def get_chat_model_for_purpose(purpose: str, streaming: bool = False) -> Tuple[Optional[BaseChatModel], Optional[Any]]:
    """
    用途に応じたChatModelを取得
    
    Args:
        purpose: 用途（'spin_generation', 'chat', 'scoring', 'scraping_analysis'）
        streaming: ストリーミングを有効化
    
    Returns:
        Tuple[BaseChatModel, AIModel]: ChatModelとAIModelのタプル
    """
    from spin.models import ModelConfiguration
    from spin.services.ai_provider_factory import AIProviderFactory
    
    try:
        config = ModelConfiguration.objects.get(purpose=purpose, is_active=True)
    except ModelConfiguration.DoesNotExist:
        logger.error(f"No active ModelConfiguration found for purpose: {purpose}")
        return None, None
    
    provider_key, model = config.get_provider_and_model()
    
    if not provider_key or not model:
        logger.error(f"No provider/model configured for purpose: {purpose}")
        return None, None
    
    try:
        service = get_langchain_service()
        temperature = float(config.temperature)
        chat_model = service.get_chat_model(provider_key, model, temperature, streaming)
        return chat_model, model
    except Exception as e:
        logger.error(f"Failed to create ChatModel for purpose {purpose}: {e}")
        
        # フォールバックを試行
        if config.has_fallback():
            fallback_key, fallback_model = config.get_fallback_provider_and_model()
            if fallback_key and fallback_model:
                try:
                    chat_model = service.get_chat_model(fallback_key, fallback_model, temperature, streaming)
                    logger.info(f"Using fallback for {purpose}: {fallback_model.model_id}")
                    return chat_model, fallback_model
                except Exception as e2:
                    logger.error(f"Fallback also failed for {purpose}: {e2}")
        
        return None, None

