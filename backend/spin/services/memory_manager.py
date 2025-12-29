"""
会話メモリ管理サービス
LangChain 1.0+対応のシンプルなメッセージ管理でコンテキスト長を自動管理
"""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

logger = logging.getLogger(__name__)


@dataclass
class MemoryConfig:
    """メモリ設定"""
    max_token_limit: int = 4000  # 最大トークン数
    max_messages: int = 50  # 最大メッセージ数
    max_chars: int = 32000  # 最大文字数


class SimpleMessageHistory:
    """シンプルなメッセージ履歴管理（LangChain 1.0+互換）"""
    
    def __init__(self):
        self.messages: List[BaseMessage] = []
    
    def add_user_message(self, content: str):
        """ユーザーメッセージを追加"""
        self.messages.append(HumanMessage(content=content))
    
    def add_ai_message(self, content: str):
        """AIメッセージを追加"""
        self.messages.append(AIMessage(content=content))
    
    def add_message(self, message: BaseMessage):
        """メッセージを追加"""
        self.messages.append(message)
    
    def get_messages(self) -> List[BaseMessage]:
        """全メッセージを取得"""
        return self.messages.copy()
    
    def clear(self):
        """メッセージをクリア"""
        self.messages.clear()


class SessionMemoryManager:
    """
    セッションごとの会話メモリを管理
    
    特徴:
    - シンプルなウィンドウベースのメモリ管理
    - トークン/文字数制限による自動トリミング
    - セッションごとにメモリを分離
    """
    
    def __init__(self):
        self._histories: Dict[str, SimpleMessageHistory] = {}
        self._summaries: Dict[str, str] = {}  # セッションごとの要約キャッシュ
    
    def get_history(self, session_id: str) -> SimpleMessageHistory:
        """セッション用の履歴を取得（なければ作成）"""
        if session_id not in self._histories:
            self._histories[session_id] = SimpleMessageHistory()
        return self._histories[session_id]
    
    def load_from_history(
        self,
        session_id: str,
        conversation_history: List[Any],
        config: Optional[MemoryConfig] = None,
    ) -> SimpleMessageHistory:
        """
        既存の会話履歴からメモリを構築
        
        Args:
            session_id: セッションID
            conversation_history: ChatMessageオブジェクトのリスト
            config: メモリ設定
        
        Returns:
            SimpleMessageHistory: 構築されたメモリ
        """
        if config is None:
            config = MemoryConfig()
        
        history = self.get_history(session_id)
        history.clear()
        
        # 最新のメッセージのみを保持
        recent = conversation_history[-config.max_messages:] if len(conversation_history) > config.max_messages else conversation_history
        
        total_chars = 0
        messages_to_add = []
        
        # 後ろから追加して文字数制限をチェック
        for msg in reversed(recent):
            role = msg.role if hasattr(msg, 'role') else str(msg.get('role', 'user'))
            content = msg.message if hasattr(msg, 'message') else str(msg.get('content', ''))
            
            if total_chars + len(content) > config.max_chars:
                break
            
            messages_to_add.insert(0, (role, content))
            total_chars += len(content)
        
        # メッセージを追加
        for role, content in messages_to_add:
            if role in ('salesperson', 'user'):
                history.add_user_message(content)
            elif role in ('customer', 'assistant'):
                history.add_ai_message(content)
        
        return history
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ):
        """メモリにメッセージを追加"""
        history = self.get_history(session_id)
        
        if role in ('salesperson', 'user'):
            history.add_user_message(content)
        elif role in ('customer', 'assistant'):
            history.add_ai_message(content)
    
    def get_messages_for_llm(
        self,
        session_id: str,
        system_prompt: str,
        config: Optional[MemoryConfig] = None,
    ) -> List[BaseMessage]:
        """
        LLMに送信するメッセージリストを取得
        
        Args:
            session_id: セッションID
            system_prompt: システムプロンプト
            config: メモリ設定
        
        Returns:
            List[BaseMessage]: LangChain形式のメッセージリスト
        """
        if config is None:
            config = MemoryConfig()
        
        messages = [SystemMessage(content=system_prompt)]
        
        history = self.get_history(session_id)
        history_messages = history.get_messages()
        
        # 文字数制限をチェック
        system_chars = len(system_prompt)
        available_chars = config.max_chars - system_chars
        
        total_chars = 0
        final_messages = []
        
        for msg in reversed(history_messages[-config.max_messages:]):
            content_len = len(msg.content)
            if total_chars + content_len > available_chars:
                break
            final_messages.insert(0, msg)
            total_chars += content_len
        
        messages.extend(final_messages)
        return messages
    
    def clear_session(self, session_id: str):
        """セッションのメモリをクリア"""
        if session_id in self._histories:
            self._histories[session_id].clear()
            del self._histories[session_id]
        
        if session_id in self._summaries:
            del self._summaries[session_id]
    
    def get_token_estimate(self, session_id: str) -> int:
        """現在のメモリの推定トークン数を取得"""
        if session_id not in self._histories:
            return 0
        
        history = self._histories[session_id]
        total_chars = sum(len(msg.content) for msg in history.get_messages())
        
        # 概算: 1トークン ≈ 4文字
        return total_chars // 4


# シングルトンインスタンス
_memory_manager: Optional[SessionMemoryManager] = None


def get_memory_manager() -> SessionMemoryManager:
    """メモリマネージャーのシングルトンインスタンスを取得"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = SessionMemoryManager()
    return _memory_manager


def prepare_messages_with_memory(
    session,
    conversation_history: List[Any],
    system_prompt: str,
    llm=None,  # LangChain 1.0+では不要だが互換性のため残す
    max_token_limit: int = 4000,
) -> List[BaseMessage]:
    """
    会話履歴とシステムプロンプトからLLM用メッセージを準備
    
    Args:
        session: Sessionオブジェクト
        conversation_history: 会話履歴
        system_prompt: システムプロンプト
        llm: LLM（互換性のため、使用しない）
        max_token_limit: 最大トークン数
    
    Returns:
        List[BaseMessage]: LangChain形式のメッセージリスト
    """
    session_id = str(session.id)
    manager = get_memory_manager()
    
    config = MemoryConfig(
        max_token_limit=max_token_limit,
        max_chars=max_token_limit * 4,  # トークン→文字数の概算
    )
    
    # 会話履歴からメモリを構築
    manager.load_from_history(session_id, conversation_history, config)
    
    # LLM用メッセージを取得
    return manager.get_messages_for_llm(session_id, system_prompt, config)


def prepare_messages_simple(
    conversation_history: List[Any],
    system_prompt: str,
    max_messages: int = 50,
    max_chars: int = 32000,
) -> List[BaseMessage]:
    """
    シンプルなメッセージ準備（文字数制限のみ）
    
    Args:
        conversation_history: 会話履歴
        system_prompt: システムプロンプト
        max_messages: 最大メッセージ数
        max_chars: 最大文字数
    
    Returns:
        List[BaseMessage]: LangChain形式のメッセージリスト
    """
    messages = [SystemMessage(content=system_prompt)]
    
    # 最新のメッセージから制限内で追加
    recent_history = list(conversation_history[-max_messages:]) if len(conversation_history) > max_messages else list(conversation_history)
    
    total_chars = len(system_prompt)
    final_history = []
    
    for msg in reversed(recent_history):
        msg_text = msg.message if hasattr(msg, 'message') else str(msg.get('content', ''))
        msg_chars = len(msg_text)
        
        if total_chars + msg_chars > max_chars:
            break
        
        final_history.insert(0, msg)
        total_chars += msg_chars
    
    # LangChain形式に変換
    for msg in final_history:
        role = msg.role if hasattr(msg, 'role') else str(msg.get('role', 'user'))
        content = msg.message if hasattr(msg, 'message') else str(msg.get('content', ''))
        
        if role in ('salesperson', 'user'):
            messages.append(HumanMessage(content=content))
        elif role in ('customer', 'assistant'):
            messages.append(AIMessage(content=content))
    
    return messages
