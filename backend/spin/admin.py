from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import Session, ChatMessage, Report, OpenAIAPIKey


# Django標準のUserモデルを一旦登録解除
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    """カスタムユーザー管理画面"""
    
    # 一覧表示
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 'session_count', 'last_login', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'date_joined', 'last_login']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    # 詳細ページのフィールドセット
    fieldsets = (
        ('ログイン情報', {
            'fields': ('username', 'password')
        }),
        ('個人情報', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('権限', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('重要な日付', {
            'fields': ('last_login', 'date_joined')
        }),
        ('統計情報', {
            'fields': ('session_count_display', 'report_count_display'),
        }),
    )
    
    # 新規ユーザー作成時のフィールドセット
    add_fieldsets = (
        ('ログイン情報', {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
        ('個人情報', {
            'fields': ('email', 'first_name', 'last_name'),
        }),
        ('権限', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
    )
    
    readonly_fields = ['last_login', 'date_joined', 'session_count_display', 'report_count_display']
    
    def session_count(self, obj):
        """セッション数を表示"""
        count = obj.sessions.count()
        return count
    session_count.short_description = 'セッション数'
    
    def session_count_display(self, obj):
        """詳細ページでセッション数を表示（リンク付き）"""
        count = obj.sessions.count()
        if count > 0:
            return format_html('<a href="/admin/spin/session/?user__id__exact={}">{} セッション</a>', obj.id, count)
        return "0 セッション"
    session_count_display.short_description = 'セッション数'
    
    def report_count_display(self, obj):
        """詳細ページでレポート数を表示"""
        count = Report.objects.filter(session__user=obj).count()
        if count > 0:
            return format_html('<a href="/admin/spin/report/?session__user__id__exact={}">{} レポート</a>', obj.id, count)
        return "0 レポート"
    report_count_display.short_description = 'レポート数'


class ChatMessageInline(admin.TabularInline):
    """セッション詳細ページで会話履歴をインライン表示"""
    model = ChatMessage
    extra = 0
    readonly_fields = ['role', 'message', 'sequence', 'created_at']
    can_delete = False
    fields = ['sequence', 'role', 'message', 'created_at']
    ordering = ['sequence']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'industry', 'status', 'message_count', 'has_report', 'started_at', 'finished_at']
    list_filter = ['status', 'created_at', 'industry']
    search_fields = ['industry', 'value_proposition', 'customer_persona', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'message_count_display', 'report_link']
    inlines = [ChatMessageInline]
    fieldsets = (
        ('基本情報', {
            'fields': ('id', 'user', 'industry', 'status')
        }),
        ('セッション情報', {
            'fields': ('value_proposition', 'customer_persona', 'customer_pain')
        }),
        ('時刻情報', {
            'fields': ('started_at', 'finished_at', 'created_at', 'updated_at')
        }),
        ('関連情報', {
            'fields': ('message_count_display', 'report_link')
        }),
    )
    
    def message_count(self, obj):
        """メッセージ数を表示"""
        count = obj.messages.count()
        return count
    message_count.short_description = 'メッセージ数'
    
    def message_count_display(self, obj):
        """詳細ページでメッセージ数を表示"""
        count = obj.messages.count()
        return f"{count}件"
    message_count_display.short_description = 'メッセージ数'
    
    def has_report(self, obj):
        """レポートの有無を表示"""
        try:
            report = obj.report
            return format_html('<span style="color: green;">✓ あり</span> (<a href="/admin/spin/report/{}/change/">詳細</a>)', report.id)
        except Report.DoesNotExist:
            return format_html('<span style="color: gray;">なし</span>')
    has_report.short_description = 'レポート'
    
    def report_link(self, obj):
        """レポートへのリンクを表示"""
        try:
            report = obj.report
            return format_html('<a href="/admin/spin/report/{}/change/">レポート詳細を表示</a>', report.id)
        except Report.DoesNotExist:
            return "レポートはまだ作成されていません"
    report_link.short_description = 'レポート'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'role', 'message_preview', 'sequence', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['message', 'session__id', 'session__industry']
    readonly_fields = ['id', 'created_at']
    list_select_related = ['session']
    
    def message_preview(self, obj):
        """メッセージのプレビュー（最初の50文字）"""
        preview = obj.message[:50]
        if len(obj.message) > 50:
            preview += "..."
        return preview
    message_preview.short_description = 'メッセージ'


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'total_score', 'situation_score', 'problem_score', 'implication_score', 'need_score', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['id', 'created_at', 'spin_scores_display', 'feedback', 'next_actions', 'scoring_details_display']
    search_fields = ['session__id', 'session__industry', 'session__user__username']
    fieldsets = (
        ('基本情報', {
            'fields': ('id', 'session', 'created_at')
        }),
        ('スコア', {
            'fields': ('spin_scores_display',)
        }),
        ('フィードバック', {
            'fields': ('feedback', 'next_actions')
        }),
        ('詳細スコア', {
            'fields': ('scoring_details_display',),
            'classes': ('collapse',)
        }),
    )
    
    def total_score(self, obj):
        """総合スコアを表示"""
        total = obj.spin_scores.get('total', 0)
        color = 'green' if total >= 80 else 'orange' if total >= 60 else 'red'
        return format_html('<span style="color: {}; font-weight: bold;">{:.1f}点</span>', color, total)
    total_score.short_description = '総合スコア'
    
    def situation_score(self, obj):
        """Situationスコアを表示"""
        score = obj.spin_scores.get('situation', 0)
        return f"{score}点"
    situation_score.short_description = 'Situation'
    
    def problem_score(self, obj):
        """Problemスコアを表示"""
        score = obj.spin_scores.get('problem', 0)
        return f"{score}点"
    problem_score.short_description = 'Problem'
    
    def implication_score(self, obj):
        """Implicationスコアを表示"""
        score = obj.spin_scores.get('implication', 0)
        return f"{score}点"
    implication_score.short_description = 'Implication'
    
    def need_score(self, obj):
        """Needスコアを表示"""
        score = obj.spin_scores.get('need', 0)
        return f"{score}点"
    need_score.short_description = 'Need'
    
    def spin_scores_display(self, obj):
        """スコアの詳細表示"""
        scores = obj.spin_scores
        html = "<table style='width: 100%; border-collapse: collapse;'>"
        html += "<tr><th style='padding: 8px; border: 1px solid #ddd;'>要素</th><th style='padding: 8px; border: 1px solid #ddd;'>スコア</th></tr>"
        for key, value in scores.items():
            if key != 'total':
                element_name = {
                    'situation': 'Situation（状況確認）',
                    'problem': 'Problem（問題発見）',
                    'implication': 'Implication（示唆）',
                    'need': 'Need（ニーズ確認）'
                }.get(key, key)
                html += f"<tr><td style='padding: 8px; border: 1px solid #ddd;'>{element_name}</td><td style='padding: 8px; border: 1px solid #ddd;'>{value}点</td></tr>"
        html += f"<tr><td style='padding: 8px; border: 1px solid #ddd; font-weight: bold;'>総合スコア</td><td style='padding: 8px; border: 1px solid #ddd; font-weight: bold;'>{scores.get('total', 0)}点</td></tr>"
        html += "</table>"
        return format_html(html)
    spin_scores_display.short_description = 'スコア詳細'
    
    def scoring_details_display(self, obj):
        """スコアリング詳細の表示"""
        if not obj.scoring_details:
            return "詳細情報はありません"
        
        html = "<div style='margin-top: 10px;'>"
        for key, details in obj.scoring_details.items():
            element_name = {
                'situation': 'Situation（状況確認）',
                'problem': 'Problem（問題発見）',
                'implication': 'Implication（示唆）',
                'need': 'Need（ニーズ確認）'
            }.get(key, key)
            
            html += f"<h4>{element_name}</h4>"
            html += f"<p><strong>スコア:</strong> {details.get('score', 0)}点</p>"
            html += f"<p><strong>コメント:</strong> {details.get('comments', '')}</p>"
            
            if details.get('strengths'):
                html += "<p><strong>強み:</strong><ul>"
                for strength in details['strengths']:
                    html += f"<li>{strength}</li>"
                html += "</ul></p>"
            
            if details.get('weaknesses'):
                html += "<p><strong>改善点:</strong><ul>"
                for weakness in details['weaknesses']:
                    html += f"<li>{weakness}</li>"
                html += "</ul></p>"
            
            html += "<hr>"
        
        html += "</div>"
        return format_html(html)
    scoring_details_display.short_description = 'スコアリング詳細'


@admin.register(OpenAIAPIKey)
class OpenAIAPIKeyAdmin(admin.ModelAdmin):
    """OpenAI APIキー管理画面"""
    
    # 一覧表示
    list_display = ['status_icon', 'name', 'purpose', 'masked_key_display', 'is_default', 'is_active', 'created_at', 'updated_at']
    list_filter = ['purpose', 'is_active', 'is_default', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['-is_default', '-is_active', '-created_at']
    
    # 詳細ページのフィールドセット
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'purpose', 'description')
        }),
        ('APIキー', {
            'fields': ('api_key',),
            'description': '⚠️ APIキーは慎重に扱ってください。外部に漏らさないよう注意してください。'
        }),
        ('設定', {
            'fields': ('is_active', 'is_default')
        }),
        ('日時情報', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    # 新規作成時のフィールドセット
    add_fieldsets = (
        ('基本情報', {
            'fields': ('name', 'purpose', 'description')
        }),
        ('APIキー', {
            'fields': ('api_key',),
        }),
        ('設定', {
            'fields': ('is_active', 'is_default')
        }),
    )
    
    def status_icon(self, obj):
        """ステータスアイコン"""
        if obj.is_active:
            color = 'green'
            icon = '✓'
            text = '有効'
        else:
            color = 'red'
            icon = '✗'
            text = '無効'
        
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 1.2em;">{}</span> {}',
            color, icon, text
        )
    status_icon.short_description = 'ステータス'
    
    def masked_key_display(self, obj):
        """マスキングされたAPIキー"""
        masked = obj.get_masked_key()
        return format_html(
            '<code style="background: #f5f5f5; padding: 4px 8px; border-radius: 3px; font-family: monospace;">{}</code>',
            masked
        )
    masked_key_display.short_description = 'APIキー'
    
    def get_form(self, request, obj=None, **kwargs):
        """フォームをカスタマイズ"""
        form = super().get_form(request, obj, **kwargs)
        
        # ヘルプテキストをカスタマイズ
        if 'api_key' in form.base_fields:
            form.base_fields['api_key'].widget.attrs.update({
                'style': 'width: 100%; font-family: monospace;',
                'placeholder': 'sk-proj-...'
            })
        
        if 'is_default' in form.base_fields:
            form.base_fields['is_default'].help_text = '✓ 同じ用途のデフォルトキーは1つのみ。チェックすると他のキーのデフォルト設定が解除されます。'
        
        return form
    
    def save_model(self, request, obj, form, change):
        """保存時の処理"""
        super().save_model(request, obj, form, change)
        
        # 保存成功メッセージ
        if change:
            self.message_user(request, f'APIキー "{obj.name}" を更新しました。', level='success')
        else:
            self.message_user(request, f'APIキー "{obj.name}" を登録しました。', level='success')

