from rest_framework import serializers
from .models import Session, ChatMessage, Report, Company, CompanyAnalysis
import uuid


class SpinGenerateSerializer(serializers.Serializer):
    industry = serializers.CharField(
        max_length=100,
        help_text="顧客の業界（必須、最大100文字）"
    )
    value_proposition = serializers.CharField(
        max_length=500,
        help_text="価値提案（必須、最大500文字）"
    )
    customer_persona = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="顧客像（オプション、最大500文字）"
    )
    customer_pain = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="顧客の課題（オプション、最大500文字）"
    )
    
    def validate_industry(self, value):
        """業界のバリデーション"""
        if not value or not value.strip():
            raise serializers.ValidationError("業界は必須です")
        return value.strip()
    
    def validate_value_proposition(self, value):
        """価値提案のバリデーション"""
        if not value or not value.strip():
            raise serializers.ValidationError("価値提案は必須です")
        if len(value.strip()) < 5:
            raise serializers.ValidationError("価値提案は5文字以上で入力してください")
        return value.strip()


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'message', 'sequence', 'created_at']
        read_only_fields = ['id', 'sequence', 'created_at']


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['id', 'user', 'industry', 'value_proposition', 'customer_persona', 
                  'customer_pain', 'status', 'started_at', 'finished_at', 'created_at']
        read_only_fields = ['id', 'user', 'status', 'started_at', 'finished_at', 'created_at']
    
    def validate_industry(self, value):
        """業界のバリデーション"""
        if not value or not value.strip():
            raise serializers.ValidationError("業界は必須です")
        return value.strip()
    
    def validate_value_proposition(self, value):
        """価値提案のバリデーション"""
        if not value or not value.strip():
            raise serializers.ValidationError("価値提案は必須です")
        if len(value.strip()) < 5:
            raise serializers.ValidationError("価値提案は5文字以上で入力してください")
        return value.strip()
    
    def create(self, validated_data):
        validated_data['id'] = uuid.uuid4()
        validated_data['status'] = 'active'
        return super().create(validated_data)


class ReportSerializer(serializers.ModelSerializer):
    session_id = serializers.UUIDField(source='session.id', read_only=True)
    
    class Meta:
        model = Report
        fields = ['id', 'session_id', 'spin_scores', 'feedback', 'next_actions', 
                  'scoring_details', 'created_at']
        read_only_fields = ['id', 'created_at']


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'source_url', 'scrape_source', 'company_name', 'industry', 
                  'business_description', 'location', 'employee_count', 'established_year',
                  'scraped_urls', 'scraped_data', 'scraped_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'scraped_at', 'created_at', 'updated_at']


class CompanyScrapeSerializer(serializers.Serializer):
    url = serializers.URLField(help_text="企業URL（必須）")
    value_proposition = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="価値提案（オプション、提案チェック用）"
    )
    
    def validate_url(self, value):
        """URLのバリデーション"""
        if not value or not value.strip():
            raise serializers.ValidationError("URLは必須です")
        return value.strip()


class CompanySitemapSerializer(serializers.Serializer):
    sitemap_url = serializers.URLField(
        required=False,
        allow_blank=True,
        help_text="sitemap.xmlのURL（ファイルアップロードの場合不要）"
    )
    value_proposition = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="価値提案（オプション、提案チェック用）"
    )
    
    def validate(self, attrs):
        """バリデーション"""
        # sitemap_urlかsitemap_fileのどちらかが必要
        if not attrs.get('sitemap_url'):
            # ファイルアップロードの場合は、views側で処理
            pass
        return attrs


class CompanyAnalysisSerializer(serializers.ModelSerializer):
    company_id = serializers.UUIDField(source='company.id', read_only=True)
    company_name = serializers.CharField(source='company.company_name', read_only=True)
    
    class Meta:
        model = CompanyAnalysis
        fields = ['id', 'company_id', 'company_name', 'value_proposition', 
                  'spin_suitability', 'recommendations', 'analysis_details',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompanyAnalyzeSerializer(serializers.Serializer):
    company_id = serializers.UUIDField(help_text="企業ID（必須）")
    value_proposition = serializers.CharField(
        max_length=500,
        help_text="価値提案（必須）"
    )
    
    def validate_company_id(self, value):
        """企業IDのバリデーション"""
        if not value:
            raise serializers.ValidationError("企業IDは必須です")
        return value
    
    def validate_value_proposition(self, value):
        """価値提案のバリデーション"""
        if not value or not value.strip():
            raise serializers.ValidationError("価値提案は必須です")
        if len(value.strip()) < 5:
            raise serializers.ValidationError("価値提案は5文字以上で入力してください")
        return value.strip()
