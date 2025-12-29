# LangChain 統合設計書

## 概要

SalesMindのAIサービスにLangChainを統合し、以下の機能を実現する：

- 統一されたプロバイダーインターフェース（OpenAI, Anthropic）
- 自動的なコンテキスト長管理
- 会話メモリ管理
- より堅牢なエラーハンドリング

## 変更履歴

| 日付 | 変更内容 |
|------|----------|
| 2025-12-29 | 初期実装（LangChain 1.0+対応） |

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                      views.py                                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   openai_client.py                           │
│  - generate_customer_response()                              │
│  - generate_spin()                                           │
│  - generate_customer_response_stream()                       │
│                                                              │
│  USE_LANGCHAIN = True の場合                                 │
│    → LangChain版を使用                                       │
│  USE_LANGCHAIN = False の場合                                │
│    → 既存の実装にフォールバック                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ langchain_      │ │ memory_         │ │ ai_provider_    │
│ service.py      │ │ manager.py      │ │ factory.py      │
│                 │ │                 │ │                 │
│ - ChatModel     │ │ - メモリ管理    │ │ - LangChain     │
│   ラッパー      │ │ - メッセージ    │ │   ChatModel     │
│ - トークン      │ │   変換          │ │   生成          │
│   カウント      │ │                 │ │                 │
└────────┬────────┘ └─────────────────┘ └────────┬────────┘
         │                                        │
         ▼                                        ▼
┌─────────────────┐                   ┌─────────────────┐
│ langchain-      │                   │ langchain-      │
│ openai          │                   │ anthropic       │
└─────────────────┘                   └─────────────────┘
```

## 追加ファイル

### 1. langchain_service.py

**場所**: `backend/spin/services/langchain_service.py`

**役割**:
- LangChain ChatModelのラッパー
- プロバイダー切り替え機能
- トークンカウント機能

**主要クラス/関数**:
- `LangChainService`: ChatModelのキャッシュと管理
- `get_langchain_service()`: シングルトンインスタンス取得
- `get_chat_model_for_purpose()`: 用途に応じたChatModel取得

### 2. memory_manager.py

**場所**: `backend/spin/services/memory_manager.py`

**役割**:
- セッションごとの会話メモリ管理
- コンテキスト長の自動制限
- メッセージ形式変換

**主要クラス/関数**:
- `SessionMemoryManager`: セッション別メモリ管理
- `SimpleMessageHistory`: LangChain 1.0+互換のメッセージ履歴
- `prepare_messages_with_memory()`: メモリ付きメッセージ準備
- `prepare_messages_simple()`: シンプルなメッセージ準備

## 設定

### requirements.txt に追加されたパッケージ

```
langchain>=0.1.0
langchain-openai>=0.0.5
langchain-anthropic>=0.1.0
langchain-community>=0.0.20
tiktoken>=0.5.0
```

### フラグ

`openai_client.py` 内の `USE_LANGCHAIN` フラグで切り替え可能：

```python
USE_LANGCHAIN = True   # LangChainを使用
USE_LANGCHAIN = False  # 既存の実装を使用
```

## コンテキスト管理

### 現在の実装

1. **文字数制限**: 会話履歴の最大文字数を制限
2. **メッセージ数制限**: 最大50件のメッセージを保持
3. **トークン推定**: 文字数/4でトークン数を概算
4. **自動トリミング**: 制限を超えた場合、古いメッセージを削除

### MemoryConfig

```python
@dataclass
class MemoryConfig:
    max_token_limit: int = 4000   # 最大トークン数
    max_messages: int = 50        # 最大メッセージ数
    max_chars: int = 32000        # 最大文字数
```

## 使用例

### 基本的な使用

```python
from spin.services.langchain_service import get_chat_model_for_purpose
from spin.services.memory_manager import prepare_messages_simple

# ChatModelを取得
chat_model, model = get_chat_model_for_purpose('chat', streaming=False)

# メッセージを準備
messages = prepare_messages_simple(
    conversation_history=history,
    system_prompt="あなたは顧客です。",
    max_messages=30,
    max_chars=16000,
)

# 呼び出し
response = chat_model.invoke(messages)
print(response.content)
```

### ストリーミング

```python
chat_model, model = get_chat_model_for_purpose('chat', streaming=True)

for chunk in chat_model.stream(messages):
    print(chunk.content, end='')
```

## エラーハンドリング

1. **ImportError**: LangChainがインストールされていない場合、既存の実装にフォールバック
2. **コンテキスト長超過**: 自動トリミングで対応、それでも超過する場合はValueError
3. **API エラー**: ログに記録し、適切なエラーメッセージを返す

## 今後の拡張

- [ ] 会話要約機能（長い会話を自動要約）
- [ ] メモリの永続化（DBへの保存）
- [ ] RAG（Retrieval-Augmented Generation）対応
- [ ] Google Gemini対応

## 注意事項

- LangChain 1.0以降では、旧メモリAPI（`ConversationSummaryBufferMemory`等）は廃止
- 現在の実装はシンプルなウィンドウベースのメモリ管理を使用
- 将来的に`langgraph`を使用した高度なメモリ管理への移行を検討

