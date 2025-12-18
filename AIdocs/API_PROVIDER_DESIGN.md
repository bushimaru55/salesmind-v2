# APIプロバイダー対応設計

## 概要

OpenAI、Claude、Geminiなど複数のAIプロバイダーに対応した柔軟なAPIキー管理システムの設計。

---

## 設計方針

### 1. **APIキーとモデルの分離**

- **1つのAPIキーで複数のモデルを使用可能**
- プロバイダーごとにAPIキーを管理
- モデル設定では「プロバイダー + モデル」を選択

### 2. **マルチプロバイダー対応**

サポートするプロバイダー：
- **OpenAI**: GPT-4o, GPT-4o-mini, GPT-5.1, GPT-5.2, etc.
- **Anthropic (Claude)**: Claude 3.5 Sonnet, Claude 3 Opus, etc.
- **Google (Gemini)**: Gemini 1.5 Pro, Gemini 1.5 Flash, etc.
- **その他**: 将来的に追加可能

### 3. **柔軟な用途別設定**

各用途（SPIN質問生成、チャット、スコアリング、スクレイピング分析）ごとに：
- プロバイダーを選択
- モデルを選択
- フォールバック設定（プライマリが失敗した場合の代替）

---

## データモデル設計

### 1. **AIProviderKey（旧: OpenAIAPIKey）**

```python
class AIProviderKey(models.Model):
    """AIプロバイダーのAPIキー管理"""
    
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic (Claude)'),
        ('google', 'Google (Gemini)'),
        ('other', 'その他'),
    ]
    
    id = UUIDField(primary_key=True)
    name = CharField(max_length=100)  # 例: "Main OpenAI API", "Claude Backup"
    provider = CharField(max_length=50, choices=PROVIDER_CHOICES)
    api_key = CharField(max_length=500)  # 暗号化推奨
    api_endpoint = URLField(null=True, blank=True)  # カスタムエンドポイント用
    description = TextField(null=True, blank=True)
    is_active = BooleanField(default=True)
    is_default = BooleanField(default=False)  # プロバイダーごとのデフォルト
    
    # メタ情報
    rate_limit_rpm = IntegerField(null=True, blank=True)  # Requests Per Minute
    rate_limit_tpm = IntegerField(null=True, blank=True)  # Tokens Per Minute
    monthly_budget = DecimalField(null=True, blank=True)  # 月間予算上限
    current_usage = DecimalField(default=0)  # 当月の使用量
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'APIキー管理'
        verbose_name_plural = 'APIキー管理'
        unique_together = [['provider', 'is_default']]  # プロバイダーごとに1つのデフォルト
```

### 2. **AIModel（新規）**

```python
class AIModel(models.Model):
    """AIモデルのマスターデータ"""
    
    provider = CharField(max_length=50, choices=AIProviderKey.PROVIDER_CHOICES)
    model_id = CharField(max_length=100)  # 例: "gpt-4o", "claude-3-5-sonnet-20241022"
    display_name = CharField(max_length=200)  # 例: "GPT-4o（高性能）"
    description = TextField(null=True, blank=True)
    
    # 性能指標
    context_window = IntegerField(null=True, blank=True)  # トークン数
    max_output_tokens = IntegerField(null=True, blank=True)
    supports_streaming = BooleanField(default=True)
    supports_function_calling = BooleanField(default=False)
    supports_vision = BooleanField(default=False)
    
    # コスト情報（USD per 1M tokens）
    input_cost_per_1m = DecimalField(max_digits=10, decimal_places=4, null=True)
    output_cost_per_1m = DecimalField(max_digits=10, decimal_places=4, null=True)
    
    # 推奨用途
    recommended_for_generation = BooleanField(default=False)
    recommended_for_chat = BooleanField(default=False)
    recommended_for_scoring = BooleanField(default=False)
    recommended_for_analysis = BooleanField(default=False)
    
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'AIモデル'
        verbose_name_plural = 'AIモデル'
        unique_together = [['provider', 'model_id']]
```

### 3. **ModelConfiguration（更新）**

```python
class ModelConfiguration(models.Model):
    """用途別モデル設定"""
    
    PURPOSE_CHOICES = [
        ('spin_generation', 'SPIN質問生成'),
        ('chat', 'チャット（顧客役）'),
        ('scoring', 'スコアリング'),
        ('scraping_analysis', 'スクレイピング分析'),
    ]
    
    purpose = CharField(max_length=50, choices=PURPOSE_CHOICES, unique=True)
    
    # プライマリ設定
    primary_provider_key = ForeignKey(
        AIProviderKey, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='primary_configs',
        help_text="メインで使用するAPIキー"
    )
    primary_model = ForeignKey(
        AIModel,
        on_delete=models.SET_NULL,
        null=True,
        related_name='primary_configs',
        help_text="メインで使用するモデル"
    )
    
    # フォールバック設定（オプション）
    fallback_provider_key = ForeignKey(
        AIProviderKey,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fallback_configs',
        help_text="プライマリが失敗した場合の代替APIキー"
    )
    fallback_model = ForeignKey(
        AIModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fallback_configs',
        help_text="プライマリが失敗した場合の代替モデル"
    )
    
    # 設定
    is_active = BooleanField(default=True)
    max_retries = IntegerField(default=3)
    timeout_seconds = IntegerField(default=30)
    temperature = DecimalField(max_digits=3, decimal_places=2, default=0.7)
    
    notes = TextField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '用途別モデル設定'
        verbose_name_plural = '用途別モデル設定'
```

---

## 使用例

### 1. **APIキー登録**

```
APIキー管理:
├─ Main OpenAI API
│  ├─ プロバイダー: OpenAI
│  ├─ APIキー: sk-xxx...
│  └─ デフォルト: ✓
│
├─ Claude Backup
│  ├─ プロバイダー: Anthropic (Claude)
│  ├─ APIキー: sk-ant-xxx...
│  └─ デフォルト: -
│
└─ Gemini API
   ├─ プロバイダー: Google (Gemini)
   ├─ APIキー: AIza...
   └─ デフォルト: ✓
```

### 2. **モデル設定**

```
用途別モデル設定:
├─ SPIN質問生成
│  ├─ プライマリ: OpenAI / GPT-5.2
│  └─ フォールバック: Anthropic / Claude 3.5 Sonnet
│
├─ チャット（顧客役）
│  ├─ プライマリ: OpenAI / GPT-4o-mini
│  └─ フォールバック: Google / Gemini 1.5 Flash
│
├─ スコアリング
│  ├─ プライマリ: Anthropic / Claude 3.5 Sonnet
│  └─ フォールバック: OpenAI / GPT-4o
│
└─ スクレイピング分析
   ├─ プライマリ: Google / Gemini 1.5 Flash
   └─ フォールバック: OpenAI / GPT-4o-mini
```

---

## サービスレイヤー設計

### 1. **AIProviderFactory**

```python
class AIProviderFactory:
    """AIプロバイダーのファクトリークラス"""
    
    @staticmethod
    def create_client(provider_key: AIProviderKey):
        """プロバイダーに応じたクライアントを生成"""
        if provider_key.provider == 'openai':
            return OpenAIClient(provider_key)
        elif provider_key.provider == 'anthropic':
            return AnthropicClient(provider_key)
        elif provider_key.provider == 'google':
            return GoogleClient(provider_key)
        else:
            raise ValueError(f"Unsupported provider: {provider_key.provider}")
```

### 2. **BaseAIClient（抽象クラス）**

```python
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
    def chat_completion(self, model: AIModel, messages: list, **kwargs):
        """チャット補完"""
        pass
    
    @abstractmethod
    def test_connection(self):
        """接続テスト"""
        pass
```

### 3. **ModelConfigurationService**

```python
class ModelConfigurationService:
    """モデル設定サービス"""
    
    @staticmethod
    def get_client_and_model(purpose: str) -> Tuple[BaseAIClient, AIModel]:
        """用途に応じたクライアントとモデルを取得"""
        config = ModelConfiguration.objects.get(purpose=purpose, is_active=True)
        
        try:
            # プライマリを試行
            client = AIProviderFactory.create_client(config.primary_provider_key)
            return client, config.primary_model
        except Exception as e:
            logger.warning(f"Primary provider failed: {e}")
            
            # フォールバックを試行
            if config.fallback_provider_key and config.fallback_model:
                client = AIProviderFactory.create_client(config.fallback_provider_key)
                return client, config.fallback_model
            
            raise ValueError(f"No available provider for purpose: {purpose}")
```

---

## マイグレーション戦略

### Phase 1: モデル追加
1. `AIProviderKey`モデルを作成（OpenAIAPIKeyから移行）
2. `AIModel`モデルを作成
3. 既存の`OpenAIAPIKey`データを`AIProviderKey`に移行

### Phase 2: ModelConfiguration更新
1. `ModelConfiguration`にForeignKeyを追加
2. 既存データを新しい構造に移行

### Phase 3: サービスレイヤー更新
1. `AIProviderFactory`を実装
2. 各プロバイダーのクライアントを実装
3. 既存のサービスを更新

### Phase 4: 管理画面更新
1. APIキー管理画面を更新
2. モデル設定画面を更新
3. モデルマスター管理画面を追加

---

## メリット

### 1. **柔軟性**
- 複数のAIプロバイダーを同時に使用可能
- 用途に応じて最適なプロバイダー/モデルを選択

### 2. **可用性**
- フォールバック機能で高可用性を実現
- プロバイダー障害時の自動切り替え

### 3. **コスト最適化**
- プロバイダーごとの料金を比較
- 用途に応じてコスト効率の良いモデルを選択

### 4. **管理性**
- APIキーを一元管理
- 使用量・コストの追跡が容易

### 5. **拡張性**
- 新しいプロバイダーの追加が容易
- プロバイダー固有の機能も実装可能

---

## 推奨モデル構成（例）

| 用途 | プライマリ | フォールバック | 理由 |
|------|----------|--------------|------|
| **SPIN質問生成** | OpenAI GPT-5.2 | Claude 3.5 Sonnet | 高品質な質問生成 |
| **チャット** | OpenAI GPT-4o-mini | Gemini 1.5 Flash | 高速応答・低コスト |
| **スコアリング** | Claude 3.5 Sonnet | OpenAI GPT-4o | 正確な評価 |
| **スクレイピング分析** | Gemini 1.5 Flash | OpenAI GPT-4o-mini | 大量テキスト処理 |

---

## 実装スケジュール

1. **Day 1-2**: データモデル設計・実装
2. **Day 3-4**: マイグレーション作成・テスト
3. **Day 5-6**: サービスレイヤー実装
4. **Day 7-8**: 管理画面更新
5. **Day 9-10**: テスト・デバッグ・ドキュメント更新

