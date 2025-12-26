from django.db import models
from django.contrib.auth.models import User
import uuid
from decimal import Decimal


class AIProviderKey(models.Model):
    """AIプロバイダーのAPIキー管理（マルチプロバイダー対応）"""
    
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic (Claude)'),
        ('google', 'Google (Gemini)'),
        ('other', 'その他'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="キーの識別名（例: Main OpenAI API, Claude Backup）")
    provider = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        default='openai',
        help_text="AIプロバイダー"
    )
    api_key = models.CharField(max_length=500, help_text="APIキー")
    api_endpoint = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="カスタムAPIエンドポイント（オプション）"
    )
    description = models.TextField(blank=True, null=True, help_text="キーの説明")
    
    # ステータス
    is_active = models.BooleanField(default=True, help_text="有効/無効")
    is_default = models.BooleanField(default=False, help_text="このプロバイダーのデフォルトキー")
    
    # レート制限・予算管理
    rate_limit_rpm = models.IntegerField(
        null=True,
        blank=True,
        help_text="レート制限（Requests Per Minute）"
    )
    rate_limit_tpm = models.IntegerField(
        null=True,
        blank=True,
        help_text="レート制限（Tokens Per Minute）"
    )
    monthly_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="月間予算上限（USD）"
    )
    current_usage = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="当月の使用量（USD）"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['provider', '-is_default', '-is_active', '-created_at']
        verbose_name = 'API統合管理'
        verbose_name_plural = 'API統合管理'
    
    def __str__(self):
        status = "✓" if self.is_active else "✗"
        default = " [デフォルト]" if self.is_default else ""
        return f"{status} {self.name} ({self.get_provider_display()}){default}"
    
    def save(self, *args, **kwargs):
        # プロバイダーごとに1つだけデフォルトを許可
        if self.is_default:
            AIProviderKey.objects.filter(
                provider=self.provider,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class AIModel(models.Model):
    """AIモデルのマスターデータ"""
    
    PROVIDER_CHOICES = AIProviderKey.PROVIDER_CHOICES
    
    provider = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        help_text="AIプロバイダー"
    )
    model_id = models.CharField(
        max_length=100,
        help_text="モデルID（例: gpt-4o, claude-3-5-sonnet-20241022）"
    )
    display_name = models.CharField(
        max_length=200,
        help_text="表示名（例: GPT-4o（高性能））"
    )
    description = models.TextField(blank=True, null=True, help_text="モデルの説明")
    
    # 性能指標
    context_window = models.IntegerField(
        null=True,
        blank=True,
        help_text="コンテキストウィンドウ（トークン数）"
    )
    max_output_tokens = models.IntegerField(
        null=True,
        blank=True,
        help_text="最大出力トークン数"
    )
    supports_streaming = models.BooleanField(default=True, help_text="ストリーミング対応")
    supports_function_calling = models.BooleanField(default=False, help_text="関数呼び出し対応")
    supports_vision = models.BooleanField(default=False, help_text="画像認識対応")
    
    # コスト情報（USD per 1M tokens）
    input_cost_per_1m = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="入力コスト（USD/1Mトークン）"
    )
    output_cost_per_1m = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="出力コスト（USD/1Mトークン）"
    )
    
    # 推奨用途
    recommended_for_generation = models.BooleanField(default=False, help_text="SPIN質問生成に推奨")
    recommended_for_chat = models.BooleanField(default=False, help_text="チャットに推奨")
    recommended_for_scoring = models.BooleanField(default=False, help_text="スコアリングに推奨")
    recommended_for_analysis = models.BooleanField(default=False, help_text="分析に推奨")
    
    is_active = models.BooleanField(default=True, help_text="有効/無効")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['provider', 'model_id']
        verbose_name = 'AIモデル'
        verbose_name_plural = 'AIモデル'
        unique_together = [['provider', 'model_id']]
    
    def __str__(self):
        return f"{self.get_provider_display()} - {self.display_name}"
    
    def get_estimated_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        """推定コストを計算"""
        if not self.input_cost_per_1m or not self.output_cost_per_1m:
            return Decimal('0.00')
        
        input_cost = (Decimal(input_tokens) / Decimal('1000000')) * self.input_cost_per_1m
        output_cost = (Decimal(output_tokens) / Decimal('1000000')) * self.output_cost_per_1m
        return input_cost + output_cost


class ModelConfiguration(models.Model):
    """用途別モデル設定（マルチプロバイダー対応）"""
    
    PURPOSE_CHOICES = [
        ('spin_generation', 'SPIN質問生成'),
        ('chat', 'チャット（顧客役）'),
        ('scoring', 'スコアリング'),
        ('scraping_analysis', 'スクレイピング分析'),
    ]
    
    purpose = models.CharField(
        max_length=50,
        choices=PURPOSE_CHOICES,
        unique=True,
        help_text="用途"
    )
    
    # プライマリ設定
    primary_provider_key = models.ForeignKey(
        AIProviderKey,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_configs',
        help_text="メインで使用するAPIキー"
    )
    primary_model = models.ForeignKey(
        AIModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_configs',
        help_text="メインで使用するモデル"
    )
    
    # フォールバック設定（オプション）
    fallback_provider_key = models.ForeignKey(
        AIProviderKey,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fallback_configs',
        help_text="プライマリが失敗した場合の代替APIキー"
    )
    fallback_model = models.ForeignKey(
        AIModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fallback_configs',
        help_text="プライマリが失敗した場合の代替モデル"
    )
    
    # レガシー対応（既存のOpenAIAPIKeyとの互換性）
    legacy_model_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="レガシーモデル名（旧システムとの互換性用）"
    )
    
    # 設定
    is_active = models.BooleanField(
        default=True,
        help_text="この設定を有効にする"
    )
    max_retries = models.IntegerField(
        default=3,
        help_text="最大リトライ回数"
    )
    timeout_seconds = models.IntegerField(
        default=30,
        help_text="タイムアウト（秒）"
    )
    temperature = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.70'),
        help_text="Temperature（0.0-1.0）"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="メモ・備考"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['purpose']
        verbose_name = '用途別モデル設定'
        verbose_name_plural = '用途別モデル設定'
    
    def __str__(self):
        if self.primary_model:
            return f"{self.get_purpose_display()}: {self.primary_model.display_name}"
        elif self.legacy_model_name:
            return f"{self.get_purpose_display()}: {self.legacy_model_name} (レガシー)"
        return f"{self.get_purpose_display()}: 未設定"
    
    def get_provider_and_model(self):
        """プライマリのプロバイダーとモデルを取得"""
        if self.primary_provider_key and self.primary_model:
            return self.primary_provider_key, self.primary_model
        return None, None
    
    def get_fallback_provider_and_model(self):
        """フォールバックのプロバイダーとモデルを取得"""
        if self.fallback_provider_key and self.fallback_model:
            return self.fallback_provider_key, self.fallback_model
        return None, None
    
    def has_fallback(self):
        """フォールバック設定があるか"""
        return bool(self.fallback_provider_key and self.fallback_model)
    
    @classmethod
    def get_config_for_purpose(cls, purpose):
        """用途に応じた設定を取得"""
        try:
            return cls.objects.get(purpose=purpose, is_active=True)
        except cls.DoesNotExist:
            return None


class OpenAIAPIKey(models.Model):
    """OpenAI APIキー管理モデル"""
    PURPOSE_CHOICES = [
        ('spin_generation', 'SPIN質問生成'),
        ('chat', 'チャット（顧客役）'),
        ('scoring', 'スコアリング'),
        ('scraping_analysis', 'スクレイピング分析'),
        ('general', '汎用'),
    ]
    
    MODEL_CHOICES = [
        ('gpt-5.2', 'GPT-5.2（最新・最高性能・推論能力強化）'),
        ('gpt-5.1', 'GPT-5.1（高性能・推論能力）'),
        ('gpt-4o', 'GPT-4o（高性能）'),
        ('gpt-4o-mini', 'GPT-4o-mini（高速・低コスト）'),
        ('gpt-4-turbo', 'GPT-4 Turbo'),
        ('gpt-4', 'GPT-4'),
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo（レガシー）'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="キーの識別名（例: 本番用、テスト用）")
    api_key = models.CharField(max_length=500, help_text="OpenAI APIキー")
    model_name = models.CharField(
        max_length=50,
        choices=MODEL_CHOICES,
        default='gpt-4o-mini',
        help_text="使用するOpenAIモデル"
    )
    purpose = models.CharField(
        max_length=50, 
        choices=PURPOSE_CHOICES, 
        default='general',
        help_text="APIキーの用途"
    )
    is_active = models.BooleanField(default=True, help_text="有効/無効")
    is_default = models.BooleanField(default=False, help_text="デフォルトキー")
    description = models.TextField(blank=True, null=True, help_text="キーの説明")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-is_active', '-created_at']
        verbose_name = 'APIキー管理'
        verbose_name_plural = 'APIキー管理'
    
    def __str__(self):
        status = "✓" if self.is_active else "✗"
        default = " [デフォルト]" if self.is_default else ""
        return f"{status} {self.name} ({self.get_purpose_display()}) - {self.model_name}{default}"
    
    def get_masked_key(self):
        """APIキーをマスキングして返す"""
        if not self.api_key:
            return ""
        if len(self.api_key) <= 12:
            return "sk-" + "*" * 8
        return self.api_key[:7] + "..." + self.api_key[-4:]
    
    def save(self, *args, **kwargs):
        # デフォルトキーが複数存在しないようにする
        if self.is_default:
            OpenAIAPIKey.objects.filter(
                purpose=self.purpose, 
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class Company(models.Model):
    """企業情報モデル"""
    SCRAPE_SOURCE_CHOICES = [
        ('url', '単一URL'),
        ('sitemap', 'sitemap.xml'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='companies')
    source_url = models.URLField(max_length=500, help_text="スクレイピング元URL（単一URL or sitemap.xml URL）")
    scrape_source = models.CharField(max_length=20, choices=SCRAPE_SOURCE_CHOICES, default='url')
    company_name = models.CharField(max_length=200)
    industry = models.CharField(max_length=100, null=True, blank=True)
    business_description = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=200, null=True, blank=True)
    employee_count = models.CharField(max_length=100, null=True, blank=True)
    established_year = models.IntegerField(null=True, blank=True)
    scraped_urls = models.JSONField(null=True, blank=True, help_text="スクレイピングしたURL一覧（sitemap.xmlの場合）")
    scraped_data = models.JSONField(null=True, blank=True, help_text="生データ保存（複数URLのデータを統合）")
    scraped_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = '企業情報'
        verbose_name_plural = '企業情報'
    
    def __str__(self):
        return f"{self.company_name} ({self.industry or '業界未設定'})"


class CompanyAnalysis(models.Model):
    """企業分析結果モデル"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='analysis')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='company_analyses')
    value_proposition = models.TextField(help_text="ユーザーが提案する価値提案")
    spin_suitability = models.JSONField(help_text="SPIN適合性スコア")
    recommendations = models.JSONField(null=True, blank=True, help_text="提案推奨事項")
    analysis_details = models.JSONField(null=True, blank=True, help_text="詳細分析結果")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = '企業分析結果'
        verbose_name_plural = '企業分析結果'
    
    def __str__(self):
        return f"Analysis for {self.company.company_name}"


class Session(models.Model):
    STATUS_CHOICES = [
        ('pending', '開始前'),
        ('active', '進行中'),
        ('finished', '完了'),
    ]
    
    MODE_CHOICES = [
        ('simple', '簡易診断'),
        ('detailed', '詳細診断'),
    ]

    SPIN_STAGE_CHOICES = [
        ('S', '状況確認 (Situation)'),
        ('P', '課題顕在化 (Problem)'),
        ('I', '示唆 (Implication)'),
        ('N', '解決メリット (Need-Payoff)'),
    ]
    
    CONVERSATION_PHASE_CHOICES = [
        ('SPIN_S', 'SPIN - 状況確認'),
        ('SPIN_P', 'SPIN - 課題顕在化'),
        ('SPIN_I', 'SPIN - 示唆'),
        ('SPIN_N', 'SPIN - 解決メリット'),
        ('CLOSING_READY', 'クロージング準備完了'),
        ('CLOSING_ACTION', 'クロージング実行中'),
        ('LOSS_CANDIDATE', '失注候補'),
        ('LOSS_CONFIRMED', '失注確定'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='simple', help_text="診断モード（簡易診断または詳細診断）")
    industry = models.CharField(max_length=100)
    value_proposition = models.TextField()
    customer_persona = models.TextField(null=True, blank=True)
    customer_pain = models.TextField(null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions', help_text="企業情報との関連付け")
    company_analysis = models.ForeignKey(CompanyAnalysis, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions', help_text="分析結果との関連付け")
    success_probability = models.IntegerField(default=50, help_text="現在の商談成功率 (0-100%)")
    last_analysis_reason = models.TextField(null=True, blank=True, help_text="直近の成功率変動理由")
    current_spin_stage = models.CharField(
        max_length=1,
        choices=SPIN_STAGE_CHOICES,
        default='S',
        help_text="現在のSPIN段階（システム判定）"
    )
    conversation_phase = models.CharField(
        max_length=20,
        choices=CONVERSATION_PHASE_CHOICES,
        default='SPIN_S',
        help_text="会話フェーズ（SPIN段階、クロージング段階、または失注段階）"
    )
    loss_reason = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="失注理由（予算不足、タイミング、必要性など）"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Session {self.id} - {self.industry}"


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('salesperson', '営業担当者'),
        ('customer', 'AI顧客'),
    ]
    STAGE_EVALUATION_CHOICES = [
        ('advance', '前進'),
        ('repeat', '同段階の継続'),
        ('regression', '逆戻り'),
        ('jump', '段階飛び越し'),
        ('unknown', '判定不能'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    message = models.TextField()
    sequence = models.PositiveIntegerField()
    success_delta = models.IntegerField(null=True, blank=True, help_text="この発言による成功率変動")
    analysis_summary = models.TextField(null=True, blank=True, help_text="成功率分析の概要")
    spin_stage = models.CharField(
        max_length=1,
        choices=Session.SPIN_STAGE_CHOICES,
        null=True,
        blank=True,
        help_text="SPIN段階（システム判定）"
    )
    stage_evaluation = models.CharField(
        max_length=20,
        choices=STAGE_EVALUATION_CHOICES,
        null=True,
        blank=True,
        help_text="段階評価（前進/同段階/逆戻り/飛び越し/判定不能）"
    )
    system_notes = models.TextField(null=True, blank=True, help_text="システムによる補足メモ")
    closing_action = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="クロージング提案の種類（見積/デモ/資料/日程調整）"
    )
    temperature_score = models.FloatField(
        null=True,
        blank=True,
        help_text="顧客温度スコア（0〜100）"
    )
    temperature_details = models.JSONField(
        null=True,
        blank=True,
        help_text="温度スコアの詳細情報（sentiment, buying_signal, cognitive_load, engagement, question_score）"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['session', 'sequence']
        indexes = [
            models.Index(fields=['session', 'sequence']),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.message[:50]}..."


class Report(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name='report')
    spin_scores = models.JSONField()
    feedback = models.TextField()
    next_actions = models.TextField()
    scoring_details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report for Session {self.session.id}"


class UserProfile(models.Model):
    """ユーザープロファイル（メール認証情報など）"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    email_verified = models.BooleanField(default=False, help_text="メールアドレスの認証状況")
    email_verified_at = models.DateTimeField(null=True, blank=True, help_text="メール認証完了日時")
    
    # マーケティング情報
    industry = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('real_estate', '不動産（売買・賃貸）'),
            ('insurance', '保険（生保・損保）'),
            ('it_saas', 'IT・SaaS'),
            ('hr', '人材（派遣・紹介）'),
            ('advertising', '広告・マーケティング'),
            ('automotive', '自動車（販売・リース）'),
            ('finance', '金融（銀行・証券）'),
            ('manufacturing', '製造業'),
            ('retail', '小売・EC'),
            ('telecom', '通信'),
            ('other', 'その他'),
        ],
        help_text="業種"
    )
    
    sales_experience = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ('less_than_1', '1年未満'),
            ('1_to_3', '1〜3年'),
            ('3_to_5', '3〜5年'),
            ('5_plus', '5年以上'),
        ],
        help_text="営業経験年数"
    )
    
    usage_purpose = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('improve_skills', '商談スキルを向上させたい'),
            ('proposal', '提案力を強化したい'),
            ('questioning', '質問力を磨きたい'),
            ('interview', '面接・転職対策'),
            ('team_training', 'チームの育成に使いたい'),
            ('other', 'その他'),
        ],
        help_text="利用目的"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    class Meta:
        verbose_name = "ユーザープロファイル"
        verbose_name_plural = "ユーザープロファイル"


class EmailVerificationToken(models.Model):
    """メール認証トークン"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verification_tokens')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="トークンの有効期限")
    used = models.BooleanField(default=False, help_text="使用済みフラグ")
    used_at = models.DateTimeField(null=True, blank=True, help_text="使用日時")
    
    def is_valid(self):
        """トークンが有効かチェック"""
        from django.utils import timezone
        return not self.used and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"Email verification token for {self.user.username}"
    
    class Meta:
        verbose_name = "メール認証トークン"
        verbose_name_plural = "メール認証トークン"
        ordering = ['-created_at']


class UserEmail(models.Model):
    """ユーザーの複数メールアドレス管理"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_emails')
    email = models.EmailField(help_text="メールアドレス")
    is_verification_email = models.BooleanField(
        default=False,
        help_text="ログイン認証メール送信用に使用するメールアドレス（1ユーザーに1つまで）"
    )
    verified = models.BooleanField(default=False, help_text="メールアドレスの認証状況")
    verified_at = models.DateTimeField(null=True, blank=True, help_text="認証完了日時")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        status = "（認証メール送信用）" if self.is_verification_email else ""
        verified_status = "認証済み" if self.verified else "未認証"
        return f"{self.email} {status} [{verified_status}]"
    
    class Meta:
        verbose_name = "ユーザーメールアドレス"
        verbose_name_plural = "ユーザーメールアドレス"
        unique_together = [['user', 'email']]  # 同一ユーザーに同じメールアドレスを重複登録できない
        ordering = ['-is_verification_email', 'created_at']
    
    def save(self, *args, **kwargs):
        """保存時にis_verification_emailの重複をチェック"""
        # 他のメールアドレスがis_verification_email=Trueの場合、それをFalseにする
        if self.is_verification_email:
            UserEmail.objects.filter(
                user=self.user,
                is_verification_email=True
            ).exclude(pk=self.pk if self.pk else None).update(is_verification_email=False)
        super().save(*args, **kwargs)


class SystemEmailAddress(models.Model):
    """システムで使用する送信元メールアドレス管理"""
    email = models.EmailField(
        unique=True,
        help_text="送信元メールアドレス（例: noreply@salesmind.mind-bridge.tech）"
    )
    name = models.CharField(
        max_length=100,
        help_text="表示名（例: SalesMind サポート）"
    )
    purpose = models.CharField(
        max_length=50,
        choices=[
            ('default', 'デフォルト（その他）'),
            ('registration', '会員登録確認'),
            ('password_reset', 'パスワードリセット'),
            ('notification', '通知'),
            ('support', 'サポート'),
            ('marketing', 'マーケティング'),
            ('system', 'システム通知'),
        ],
        default='default',
        help_text="メール送信の用途"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="有効/無効"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="デフォルト送信元として使用"
    )
    description = models.TextField(
        blank=True,
        help_text="説明・用途メモ"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'email_management'
        db_table = 'spin_systememailaddress'  # 既存のテーブル名を保持
        verbose_name = "システムメールアドレス"
        verbose_name_plural = "システムメールアドレス"
        ordering = ['-is_default', 'purpose', 'email']
    
    def __str__(self):
        return f"{self.email} ({self.get_purpose_display()})"
    
    def save(self, *args, **kwargs):
        """is_defaultがTrueの場合、他のis_defaultをFalseに"""
        if self.is_default:
            SystemEmailAddress.objects.filter(
                is_default=True
            ).exclude(pk=self.pk if self.pk else None).update(is_default=False)
        super().save(*args, **kwargs)


class EmailTemplate(models.Model):
    """メールテンプレート管理"""
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="テンプレート名（例: registration_email）"
    )
    display_name = models.CharField(
        max_length=200,
        help_text="表示名（例: 会員登録確認メール）"
    )
    purpose = models.CharField(
        max_length=50,
        choices=[
            ('registration', '会員登録確認'),
            ('password_reset', 'パスワードリセット'),
            ('notification', '通知'),
            ('welcome', 'ウェルカムメール'),
            ('other', 'その他'),
        ],
        default='other',
        help_text="メールの用途"
    )
    from_email = models.ForeignKey(
        'SystemEmailAddress',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_templates',
        help_text="送信元メールアドレス（空欄の場合はデフォルトを使用）"
    )
    subject = models.CharField(
        max_length=200,
        help_text="件名（変数使用可: {username}, {site_name}等）"
    )
    body_text = models.TextField(
        help_text="本文（テキスト版）\n変数使用可: {username}, {verification_url}, {site_name}等"
    )
    body_html = models.TextField(
        blank=True,
        help_text="本文（HTML版・オプション）\n変数使用可: {username}, {verification_url}, {site_name}等"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="有効/無効"
    )
    available_variables = models.TextField(
        blank=True,
        help_text="利用可能な変数のリスト（参考用、カンマ区切り）\n例: username, email, verification_url, site_name"
    )
    description = models.TextField(
        blank=True,
        help_text="説明・用途メモ"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'email_management'
        db_table = 'email_management_emailtemplate'
        verbose_name = "メールテンプレート"
        verbose_name_plural = "メールテンプレート"
        ordering = ['purpose', 'name']
    
    def __str__(self):
        return f"{self.display_name} ({self.name})"
    
    def render(self, context):
        """テンプレートを変数で置換してレンダリング"""
        subject = self.subject.format(**context)
        body_text = self.body_text.format(**context)
        body_html = self.body_html.format(**context) if self.body_html else None
        return subject, body_text, body_html

