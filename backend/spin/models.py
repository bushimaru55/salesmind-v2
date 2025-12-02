from django.db import models
from django.contrib.auth.models import User
import uuid


class OpenAIAPIKey(models.Model):
    """OpenAI APIキー管理モデル"""
    PURPOSE_CHOICES = [
        ('spin_generation', 'SPIN質問生成'),
        ('chat', 'チャット（顧客役）'),
        ('scoring', 'スコアリング'),
        ('scraping_analysis', 'スクレイピング分析'),
        ('general', '汎用'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="キーの識別名（例: 本番用、テスト用）")
    api_key = models.CharField(max_length=500, help_text="OpenAI APIキー")
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
        verbose_name = 'OpenAI APIキー'
        verbose_name_plural = 'OpenAI APIキー'
    
    def __str__(self):
        status = "✓" if self.is_active else "✗"
        default = " [デフォルト]" if self.is_default else ""
        return f"{status} {self.name} ({self.get_purpose_display()}){default}"
    
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

