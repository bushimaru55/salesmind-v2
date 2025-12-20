from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import Session, ChatMessage, Report, OpenAIAPIKey, ModelConfiguration, AIProviderKey, AIModel
import openai
import logging

logger = logging.getLogger(__name__)

# 管理画面のカスタマイズ
admin.site.site_header = 'SalesMind 管理画面'
admin.site.site_title = 'SalesMind Admin'
admin.site.index_title = 'ダッシュボード'

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


# 旧OpenAIAPIKeyは非表示（互換性のため残存）
# @admin.register(OpenAIAPIKey)
class OpenAIAPIKeyAdmin(admin.ModelAdmin):
    """OpenAI APIキー管理画面（レガシー・非表示）"""
    
    # 一覧表示
    list_display = ['name', 'purpose', 'model_name', 'masked_key_display', 'is_default', 'is_active', 'status_icon', 'created_at', 'updated_at', 'test_connection_link', 'edit_link']
    list_filter = ['purpose', 'model_name', 'is_active', 'is_default', 'created_at']
    search_fields = ['name', 'description', 'model_name']
    ordering = ['-is_default', '-is_active', '-created_at']
    list_editable = ['is_default', 'is_active']  # 一覧画面で直接編集可能
    actions = ['activate_keys', 'deactivate_keys', 'duplicate_key', 'test_api_keys']  # カスタムアクション
    
    # 詳細ページのフィールドセット
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'purpose', 'description')
        }),
        ('APIキー設定', {
            'fields': ('api_key', 'model_name', 'test_result_display', 'test_chat_display'),
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
    
    readonly_fields = ['created_at', 'updated_at', 'test_result_display', 'test_chat_display']
    
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
    
    def test_connection_link(self, obj):
        """疎通テストリンク"""
        from django.utils.safestring import mark_safe
        return mark_safe(
            f'<a href="#" onclick="testAPIKey(\'{obj.id}\'); return false;" '
            f'style="color: #417690; text-decoration: none; cursor: pointer;" '
            f'id="test-link-{obj.id}">🔌 疎通テスト</a>'
        )
    test_connection_link.short_description = '接続テスト'
    
    def edit_link(self, obj):
        """編集リンク"""
        from django.urls import reverse
        from django.utils.safestring import mark_safe
        url = reverse('admin:spin_openaiapikey_change', args=[obj.id])
        return mark_safe(f'<a href="{url}" style="color: #417690; text-decoration: none;">✎ 編集</a>')
    edit_link.short_description = '操作'
    
    def test_result_display(self, obj):
        """疎通テスト結果表示エリア"""
        from django.utils.safestring import mark_safe
        return mark_safe(
            f'<div id="test-result-{obj.id}" style="margin-top: 10px;">'
            f'<button type="button" onclick="testAPIKeyDetail(\'{obj.id}\')" '
            f'style="padding: 8px 16px; background: #417690; color: white; border: none; '
            f'border-radius: 4px; cursor: pointer; font-size: 14px;">🔌 疎通テストを実行</button>'
            f'<div id="test-status-{obj.id}" style="margin-top: 10px;"></div>'
            f'</div>'
        )
    test_result_display.short_description = '疎通テスト'
    
    def test_chat_display(self, obj):
        """テストチャット表示エリア"""
        from django.utils.safestring import mark_safe
        return mark_safe(
            f'<div id="test-chat-{obj.id}" style="margin-top: 20px; border: 1px solid #ddd; border-radius: 4px; padding: 15px; background: #f9f9f9;">'
            f'<h3 style="margin-top: 0; color: #333;">💬 テストチャット</h3>'
            f'<p style="color: #666; font-size: 13px;">このAPIキーとモデルを使用して実際にチャットをテストできます。</p>'
            f'<div id="chat-history-{obj.id}" style="max-height: 400px; overflow-y: auto; background: white; border: 1px solid #ddd; border-radius: 4px; padding: 10px; margin-bottom: 10px; min-height: 200px;"></div>'
            f'<div style="display: flex; gap: 10px;">'
            f'<textarea id="chat-input-{obj.id}" placeholder="メッセージを入力してください..." '
            f'style="flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 4px; resize: vertical; min-height: 60px; font-family: inherit;"></textarea>'
            f'<button type="button" onclick="sendTestMessage(\'{obj.id}\')" '
            f'style="padding: 10px 20px; background: #417690; color: white; border: none; '
            f'border-radius: 4px; cursor: pointer; font-size: 14px; white-space: nowrap;">送信</button>'
            f'</div>'
            f'<div style="margin-top: 10px;">'
            f'<button type="button" onclick="clearChatHistory(\'{obj.id}\')" '
            f'style="padding: 6px 12px; background: #999; color: white; border: none; '
            f'border-radius: 4px; cursor: pointer; font-size: 12px;">履歴をクリア</button>'
            f'</div>'
            f'</div>'
        )
    test_chat_display.short_description = 'テストチャット'
    
    def save_model(self, request, obj, form, change):
        """保存時の処理"""
        super().save_model(request, obj, form, change)
        
        # 保存成功メッセージ
        if change:
            self.message_user(request, f'APIキー "{obj.name}" を更新しました。', level='success')
        else:
            self.message_user(request, f'APIキー "{obj.name}" を登録しました。', level='success')
    
    def delete_model(self, request, obj):
        """削除時の処理"""
        key_name = obj.name
        purpose = obj.get_purpose_display()
        super().delete_model(request, obj)
        self.message_user(request, f'APIキー "{key_name}" ({purpose}) を削除しました。', level='warning')
    
    def delete_queryset(self, request, queryset):
        """一括削除時の処理"""
        count = queryset.count()
        super().delete_queryset(request, queryset)
        self.message_user(request, f'{count}個のAPIキーを削除しました。', level='warning')
    
    # カスタムアクション
    @admin.action(description='選択したAPIキーを有効化')
    def activate_keys(self, request, queryset):
        """選択したAPIキーを有効化"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated}個のAPIキーを有効化しました。', level='success')
    
    @admin.action(description='選択したAPIキーを無効化')
    def deactivate_keys(self, request, queryset):
        """選択したAPIキーを無効化"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}個のAPIキーを無効化しました。', level='success')
    
    @admin.action(description='選択したAPIキーを複製')
    def duplicate_key(self, request, queryset):
        """選択したAPIキーを複製"""
        if queryset.count() > 1:
            self.message_user(request, '複製は1つずつ行ってください。', level='error')
            return
        
        original = queryset.first()
        duplicate = OpenAIAPIKey.objects.create(
            name=f"{original.name} (コピー)",
            api_key=original.api_key,
            purpose=original.purpose,
            is_active=False,  # 複製したキーは無効状態で作成
            is_default=False,
            description=f"[複製] {original.description or ''}"
        )
        self.message_user(request, f'APIキー "{duplicate.name}" を複製しました。（無効状態）', level='success')
    
    @admin.action(description='選択したAPIキーの疎通テストを実行')
    def test_api_keys(self, request, queryset):
        """選択したAPIキーの疎通テストを実行"""
        results = []
        for api_key_obj in queryset:
            result = self._test_single_api_key(api_key_obj)
            results.append(f"{api_key_obj.name}: {result['status']} - {result['message']}")
        
        message = "\n".join(results)
        self.message_user(request, f"疎通テスト結果:\n{message}", level='info')
    
    def _test_single_api_key(self, api_key_obj):
        """単一のAPIキーをテスト"""
        try:
            client = openai.OpenAI(api_key=api_key_obj.api_key)
            
            # 設定されたモデルでテスト
            response = client.chat.completions.create(
                model=api_key_obj.model_name,
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
                max_tokens=5
            )
            
            return {
                'status': '✓ 成功',
                'message': f'接続成功（モデル: {response.model}）',
                'success': True
            }
        except openai.AuthenticationError:
            return {
                'status': '✗ 認証エラー',
                'message': 'APIキーが無効です',
                'success': False
            }
        except openai.RateLimitError:
            return {
                'status': '⚠ レート制限',
                'message': 'レート制限に達しています',
                'success': False
            }
        except openai.APIConnectionError:
            return {
                'status': '✗ 接続エラー',
                'message': 'OpenAI APIに接続できません',
                'success': False
            }
        except Exception as e:
            logger.error(f"API Key test failed: {str(e)}")
            return {
                'status': '✗ エラー',
                'message': str(e),
                'success': False
            }
    
    def get_urls(self):
        """カスタムURLを追加"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'test-api-key/<uuid:key_id>/',
                self.admin_site.admin_view(self.test_api_key_view),
                name='spin_openaiapikey_test',
            ),
            path(
                'test-chat/<uuid:key_id>/',
                self.admin_site.admin_view(self.test_chat_view),
                name='spin_openaiapikey_test_chat',
            ),
        ]
        return custom_urls + urls
    
    def test_api_key_view(self, request, key_id):
        """APIキー疎通テストのビュー"""
        try:
            api_key_obj = OpenAIAPIKey.objects.get(id=key_id)
            result = self._test_single_api_key(api_key_obj)
            
            return JsonResponse({
                'success': result['success'],
                'status': result['status'],
                'message': result['message'],
                'key_name': api_key_obj.name
            })
        except OpenAIAPIKey.DoesNotExist:
            return JsonResponse({
                'success': False,
                'status': '✗ エラー',
                'message': 'APIキーが見つかりません'
            }, status=404)
        except Exception as e:
            logger.error(f"Test API key view error: {str(e)}")
            return JsonResponse({
                'success': False,
                'status': '✗ エラー',
                'message': str(e)
            }, status=500)
    
    def test_chat_view(self, request, key_id):
        """テストチャットのビュー"""
        import json
        
        if request.method != 'POST':
            return JsonResponse({
                'success': False,
                'message': 'POSTメソッドのみサポートしています'
            }, status=405)
        
        try:
            api_key_obj = OpenAIAPIKey.objects.get(id=key_id)
            
            # リクエストボディからメッセージと会話履歴を取得
            body = json.loads(request.body)
            user_message = body.get('message', '')
            chat_history = body.get('history', [])
            
            if not user_message:
                return JsonResponse({
                    'success': False,
                    'message': 'メッセージが空です'
                }, status=400)
            
            # OpenAIクライアントを作成
            client = openai.OpenAI(api_key=api_key_obj.api_key)
            
            # 会話履歴を構築
            messages = []
            for msg in chat_history:
                messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
            
            # ユーザーメッセージを追加
            messages.append({
                'role': 'user',
                'content': user_message
            })
            
            # OpenAI APIを呼び出し
            response = client.chat.completions.create(
                model=api_key_obj.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            assistant_message = response.choices[0].message.content
            
            logger.info(f"テストチャット成功: key={api_key_obj.name}, model={api_key_obj.model_name}")
            
            return JsonResponse({
                'success': True,
                'message': assistant_message,
                'model': response.model,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            })
            
        except OpenAIAPIKey.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'APIキーが見つかりません'
            }, status=404)
        except openai.AuthenticationError:
            return JsonResponse({
                'success': False,
                'message': 'APIキーが無効です'
            }, status=401)
        except openai.RateLimitError:
            return JsonResponse({
                'success': False,
                'message': 'レート制限に達しています'
            }, status=429)
        except openai.APIConnectionError:
            return JsonResponse({
                'success': False,
                'message': 'OpenAI APIに接続できません'
            }, status=503)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'リクエストボディが不正です'
            }, status=400)
        except Exception as e:
            logger.error(f"テストチャットエラー: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': f'エラーが発生しました: {str(e)}'
            }, status=500)
    
    class Media:
        """管理画面用のJavaScript追加"""
        js = ('admin/js/api_key_test.js',)


@admin.register(ModelConfiguration)
class ModelConfigurationAdmin(admin.ModelAdmin):
    """用途別モデル設定管理画面"""
    
    # 一覧表示
    list_display = ['purpose_display', 'primary_model_display', 'fallback_model_display', 'is_active', 'updated_at']
    list_filter = ['is_active', 'purpose']
    list_editable = ['is_active']
    ordering = ['purpose']
    actions = ['activate_configs']
    
    # 詳細ページのフィールドセット
    fieldsets = (
        ('基本情報', {
            'fields': ('purpose', 'is_active')
        }),
        ('プライマリ設定', {
            'fields': ('primary_provider_key', 'primary_model')
        }),
        ('フォールバック設定（オプション）', {
            'fields': ('fallback_provider_key', 'fallback_model'),
            'classes': ('collapse',)
        }),
        ('詳細設定', {
            'fields': ('max_retries', 'timeout_seconds', 'temperature'),
            'classes': ('collapse',)
        }),
        ('メモ', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('日時情報', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    class Media:
        js = ('admin/js/model_configuration.js',)
    
    def purpose_display(self, obj):
        """用途の表示"""
        return obj.get_purpose_display()
    purpose_display.short_description = '用途'
    purpose_display.admin_order_field = 'purpose'
    
    def primary_model_display(self, obj):
        """プライマリモデルの表示"""
        provider_key, model = obj.get_provider_and_model()
        if provider_key and model:
            return format_html(
                '<strong>{}</strong><br><span style="color: #666; font-size: 12px;">{}</span>',
                model.display_name,
                provider_key.name
            )
        return format_html('<span style="color: #dc3545;">未設定</span>')
    primary_model_display.short_description = 'プライマリモデル'
    
    def fallback_model_display(self, obj):
        """フォールバックモデルの表示"""
        fallback_key, fallback_model = obj.get_fallback_provider_and_model()
        if fallback_key and fallback_model:
            return format_html(
                '{}<br><span style="color: #666; font-size: 12px;">{}</span>',
                fallback_model.display_name,
                fallback_key.name
            )
        return format_html('<span style="color: #999;">-</span>')
    fallback_model_display.short_description = 'フォールバック'
    
    def status_display(self, obj):
        """ステータス表示"""
        if obj.is_active:
            color = 'green'
            icon = '✓'
            text = '有効'
        else:
            color = 'red'
            icon = '✗'
            text = '無効'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span> {}',
            color, icon, text
        )
    status_display.short_description = 'ステータス'
    
    def get_form(self, request, obj=None, **kwargs):
        """フォームをカスタマイズ"""
        form = super().get_form(request, obj, **kwargs)
        
        # 用途フィールドのヘルプテキストをカスタマイズ
        if 'purpose' in form.base_fields:
            form.base_fields['purpose'].help_text = 'この設定を適用する用途を選択してください'
        
        # Primary modelの選択肢をフィルタリング
        if 'primary_model' in form.base_fields:
            # 現在選択されているprimary_provider_keyを取得
            provider_key = None
            if obj and obj.primary_provider_key:
                provider_key = obj.primary_provider_key
            elif request.POST and 'primary_provider_key' in request.POST:
                try:
                    provider_key_id = request.POST.get('primary_provider_key')
                    if provider_key_id:
                        provider_key = AIProviderKey.objects.get(id=provider_key_id)
                except (AIProviderKey.DoesNotExist, ValueError):
                    pass
            
            if provider_key:
                # 選択されたプロバイダーのモデルのみを表示
                available_models = AIModel.objects.filter(
                    provider=provider_key.provider,
                    is_active=True
                ).order_by('model_id')
                
                # 選択肢を更新
                form.base_fields['primary_model'].queryset = available_models
                form.base_fields['primary_model'].help_text = (
                    f'💡 {provider_key.get_provider_display()}のモデルのみ表示されています。'
                    f'（APIキー: {provider_key.name}）'
                )
            else:
                # プロバイダーキーが選択されていない場合は、空のクエリセットを設定
                # JavaScriptが動的に選択肢を更新するため、初期状態では空にする
                form.base_fields['primary_model'].queryset = AIModel.objects.none()
                form.base_fields['primary_model'].help_text = (
                    '💡 先に「Primary provider key」を選択すると、そのプロバイダーのモデルのみが表示されます。'
                )
        
        # Fallback modelも同様にフィルタリング
        if 'fallback_model' in form.base_fields:
            fallback_provider_key = None
            if obj and obj.fallback_provider_key:
                fallback_provider_key = obj.fallback_provider_key
            elif request.POST and 'fallback_provider_key' in request.POST:
                try:
                    fallback_provider_key_id = request.POST.get('fallback_provider_key')
                    if fallback_provider_key_id:
                        fallback_provider_key = AIProviderKey.objects.get(id=fallback_provider_key_id)
                except (AIProviderKey.DoesNotExist, ValueError):
                    pass
            
            if fallback_provider_key:
                available_models = AIModel.objects.filter(
                    provider=fallback_provider_key.provider,
                    is_active=True
                ).order_by('model_id')
                
                form.base_fields['fallback_model'].queryset = available_models
                form.base_fields['fallback_model'].help_text = (
                    f'💡 {fallback_provider_key.get_provider_display()}のモデルのみ表示されています。'
                    f'（APIキー: {fallback_provider_key.name}）'
                )
            else:
                # プロバイダーキーが選択されていない場合は、空のクエリセットを設定
                # JavaScriptが動的に選択肢を更新するため、初期状態では空にする
                form.base_fields['fallback_model'].queryset = AIModel.objects.none()
                form.base_fields['fallback_model'].help_text = (
                    '💡 先に「Fallback provider key」を選択すると、そのプロバイダーのモデルのみが表示されます。'
                )
        
        return form
    
    def save_model(self, request, obj, form, change):
        """保存時の処理"""
        super().save_model(request, obj, form, change)
        
        provider_key, model = obj.get_provider_and_model()
        if provider_key and model:
            self.message_user(
                request,
                f'✓ {obj.get_purpose_display()}に{model.display_name}を設定しました。',
                level=messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                f'{obj.get_purpose_display()}の設定を保存しました。',
                level=messages.INFO
            )
    
    @admin.action(description='選択した設定を有効化')
    def activate_configs(self, request, queryset):
        """選択した設定を有効化"""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            f'✓ {count}件の設定を有効化しました。',
            level=messages.SUCCESS
        )
    
    def changelist_view(self, request, extra_context=None):
        """一覧画面のカスタマイズ"""
        from django.utils.safestring import mark_safe
        
        extra_context = extra_context or {}
        
        # タイトル
        extra_context['title'] = '用途別モデル設定'
        
        # 全ての用途の設定が存在するか確認（初期化ボタンは不要になったため削除）
        all_purposes = [choice[0] for choice in ModelConfiguration.PURPOSE_CHOICES]
        existing_purposes = set(ModelConfiguration.objects.values_list('purpose', flat=True))
        missing_purposes = set(all_purposes) - existing_purposes
        
        if missing_purposes:
            extra_context['missing_purposes'] = missing_purposes
        
        # 推奨モデル情報を取得
        from spin.models import AIModel
        recommended_models = {}
        for purpose_code, purpose_name in ModelConfiguration.PURPOSE_CHOICES:
            if purpose_code == 'spin_generation':
                models = AIModel.objects.filter(recommended_for_generation=True, is_active=True).first()
            elif purpose_code == 'chat':
                models = AIModel.objects.filter(recommended_for_chat=True, is_active=True).first()
            elif purpose_code == 'scoring':
                models = AIModel.objects.filter(recommended_for_scoring=True, is_active=True).first()
            elif purpose_code == 'scraping_analysis':
                models = AIModel.objects.filter(recommended_for_analysis=True, is_active=True).first()
            else:
                models = None
            
            if models:
                recommended_models[purpose_code] = models.display_name
        
        extra_context['recommended_models'] = recommended_models
        
        return super().changelist_view(request, extra_context)
    
    def get_urls(self):
        """カスタムURLを追加"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'apply-recommended/',
                self.admin_site.admin_view(self.apply_recommended_view),
                name='spin_modelconfiguration_apply_recommended',
            ),
            path(
                'get-models-for-provider/',
                self.admin_site.admin_view(self.get_models_for_provider_view),
                name='spin_modelconfiguration_get_models_for_provider',
            ),
        ]
        return custom_urls + urls
    
    def apply_recommended_view(self, request):
        """推奨設定適用のビュー - APIキーが登録されており利用可能なモデルから自動適用"""
        if request.method != 'POST':
            return redirect('admin:spin_modelconfiguration_changelist')
        
        from django.db import transaction
        from django.utils.safestring import mark_safe
        
        try:
            applied_count = 0
            skipped_count = 0
            errors = []
            applied_details = []
            
            with transaction.atomic():
                # まず、全ての用途に推奨されているモデルを検索（優先度：最高）
                universal_model = AIModel.objects.filter(
                    recommended_for_generation=True,
                    recommended_for_chat=True,
                    recommended_for_scoring=True,
                    recommended_for_analysis=True,
                    is_active=True
                ).first()
                
                universal_provider_key = None
                if universal_model:
                    # 全用途対応モデルに対応するAPIキーを取得
                    universal_provider_key = AIProviderKey.objects.filter(
                        provider=universal_model.provider,
                        is_active=True
                    ).order_by('-is_default', '-created_at').first()
                
                # 全用途対応モデルとAPIキーが存在する場合、全ての用途に適用
                if universal_model and universal_provider_key:
                    for purpose_code, purpose_name in ModelConfiguration.PURPOSE_CHOICES:
                        try:
                            config = ModelConfiguration.objects.get(purpose=purpose_code)
                            config.primary_provider_key = universal_provider_key
                            config.primary_model = universal_model
                            config.is_active = True
                            config.save(update_fields=['primary_provider_key', 'primary_model', 'is_active', 'updated_at'])
                            action = '更新'
                        except ModelConfiguration.DoesNotExist:
                            config = ModelConfiguration.objects.create(
                                purpose=purpose_code,
                                primary_provider_key=universal_provider_key,
                                primary_model=universal_model,
                                is_active=True,
                            )
                            action = '作成'
                        
                        applied_count += 1
                        applied_details.append(f"{purpose_name}: {universal_model.display_name} ({action})")
                else:
                    # 全用途対応モデルがない場合、各用途ごとに個別に推奨モデルを検索
                    for purpose_code, purpose_name in ModelConfiguration.PURPOSE_CHOICES:
                        # 推奨フラグが立っているモデルを取得
                        recommended_model = None
                        if purpose_code == 'spin_generation':
                            recommended_model = AIModel.objects.filter(
                                recommended_for_generation=True,
                                is_active=True
                            ).first()
                        elif purpose_code == 'chat':
                            recommended_model = AIModel.objects.filter(
                                recommended_for_chat=True,
                                is_active=True
                            ).first()
                        elif purpose_code == 'scoring':
                            recommended_model = AIModel.objects.filter(
                                recommended_for_scoring=True,
                                is_active=True
                            ).first()
                        elif purpose_code == 'scraping_analysis':
                            recommended_model = AIModel.objects.filter(
                                recommended_for_analysis=True,
                                is_active=True
                            ).first()
                        
                        if not recommended_model:
                            skipped_count += 1
                            errors.append(f"{purpose_name}: 推奨モデルが見つかりません")
                            continue
                        
                        # そのモデルに対応するAPIキーを取得（is_active=True、is_default優先）
                        provider_key = AIProviderKey.objects.filter(
                            provider=recommended_model.provider,
                            is_active=True
                        ).order_by('-is_default', '-created_at').first()
                        
                        if not provider_key:
                            skipped_count += 1
                            errors.append(f"{purpose_name}: {recommended_model.display_name}に対応するAPIキーが登録されていません")
                            continue
                        
                        # ModelConfigurationを作成または更新
                        try:
                            config = ModelConfiguration.objects.get(purpose=purpose_code)
                            # 既存の設定を更新
                            config.primary_provider_key = provider_key
                            config.primary_model = recommended_model
                            config.is_active = True
                            config.save(update_fields=['primary_provider_key', 'primary_model', 'is_active', 'updated_at'])
                            action = '更新'
                        except ModelConfiguration.DoesNotExist:
                            # 新規作成
                            config = ModelConfiguration.objects.create(
                                purpose=purpose_code,
                                primary_provider_key=provider_key,
                                primary_model=recommended_model,
                                is_active=True,
                            )
                            action = '作成'
                        
                        applied_count += 1
                        applied_details.append(f"{purpose_name}: {recommended_model.display_name} ({action})")
            
            # 結果メッセージを表示
            if applied_count > 0:
                detail_message = '<br>'.join(applied_details)
                messages.success(
                    request,
                    mark_safe(f'✅ {applied_count}件の推奨設定を適用しました。<br>{detail_message}')
                )
            if skipped_count > 0:
                messages.warning(
                    request,
                    f'⚠️ {skipped_count}件の設定はスキップされました（APIキー未登録または推奨モデル未設定）。'
                )
            if errors:
                for error in errors:
                    messages.warning(request, f'⚠️ {error}')
            
        except Exception as e:
            logger.error(f"Error applying recommended settings: {e}", exc_info=True)
            messages.error(
                request,
                f'❌ 推奨設定の適用中にエラーが発生しました: {str(e)}'
            )
        
        return redirect('admin:spin_modelconfiguration_changelist')
    
    def get_models_for_provider_view(self, request):
        """プロバイダーキーに対応するモデル一覧を取得（AJAX用）"""
        if request.method != 'POST':
            return JsonResponse({'success': False, 'message': 'Invalid request method'})
        
        import json
        try:
            data = json.loads(request.body)
            provider_key_id = data.get('provider_key_id')
            
            if not provider_key_id:
                return JsonResponse({'success': False, 'message': 'Provider key ID is required'})
            
            provider_key = AIProviderKey.objects.get(id=provider_key_id, is_active=True)
            
            # そのプロバイダーのモデル一覧を取得
            models = AIModel.objects.filter(
                provider=provider_key.provider,
                is_active=True
            ).order_by('model_id')
            
            models_data = [
                {
                    'id': model.id,
                    'display_name': f'{model.get_provider_display()} - {model.display_name}'
                }
                for model in models
            ]
            
            return JsonResponse({
                'success': True,
                'models': models_data,
                'provider': provider_key.get_provider_display()
            })
        
        except AIProviderKey.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Provider key not found'})
        except Exception as e:
            logger.error(f"Error getting models for provider: {e}")
            return JsonResponse({'success': False, 'message': str(e)})


@admin.register(AIProviderKey)
class AIProviderKeyAdmin(admin.ModelAdmin):
    """API統合管理画面（OpenAI、Claude、Geminiなど全てのAIプロバイダーを統合管理）"""
    
    # 一覧表示
    list_display = ['name', 'provider_display', 'is_active', 'is_default', 'usage_display', 'created_at']
    list_filter = ['provider', 'is_active', 'is_default', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['provider', '-is_default', '-is_active', '-created_at']
    
    def changelist_view(self, request, extra_context=None):
        """一覧画面のカスタマイズ"""
        from django.utils.safestring import mark_safe
        
        extra_context = extra_context or {}
        extra_context['title'] = 'API統合管理'
        extra_context['subtitle'] = mark_safe(
            '<div style="background: #e7f3ff; padding: 15px; border-left: 4px solid #2196F3; margin-bottom: 20px;">'
            '<strong>💡 API統合管理とは？</strong><br>'
            '<p style="margin: 10px 0;">OpenAI、Claude、Geminiなど、複数のAIプロバイダーのAPIキーを一元管理します。</p>'
            '<p style="margin: 10px 0;"><strong>重要:</strong> 1つのAPIキーで、そのプロバイダーの<strong>全てのモデル</strong>を使用できます。</p>'
            '<ul style="margin: 10px 0 0 20px; padding: 0;">'
            '<li>🤖 <strong>OpenAI:</strong> GPT-4o、GPT-5.2など全モデル</li>'
            '<li>🧠 <strong>Anthropic (Claude):</strong> Claude 3.5 Sonnet、Claude 3 Opusなど全モデル</li>'
            '<li>🔍 <strong>Google (Gemini):</strong> Gemini 1.5 Pro、Gemini 1.5 Flashなど全モデル</li>'
            '</ul>'
            '</div>'
        )
        return super().changelist_view(request, extra_context)
    
    # ヘルプテキスト
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['provider'].help_text = (
            '💡 <strong>重要:</strong> 1つのAPIキーで、そのプロバイダーの全てのモデルを使用できます。<br>'
            '例: OpenAI APIキー1つで、GPT-4o、GPT-5.2など全てのOpenAIモデルが利用可能です。'
        )
        return form
    
    # 詳細ページのフィールドセット
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'provider', 'description')
        }),
        ('APIキー設定', {
            'fields': ('api_key', 'api_endpoint', 'test_result_display'),
            'description': '⚠️ APIキーは慎重に扱ってください。外部に漏らさないよう注意してください。'
        }),
        ('ステータス', {
            'fields': ('is_active', 'is_default')
        }),
        ('レート制限・予算管理', {
            'fields': ('rate_limit_rpm', 'rate_limit_tpm', 'monthly_budget', 'current_usage'),
            'classes': ('collapse',)
        }),
        ('日時情報', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'test_result_display']
    
    def provider_display(self, obj):
        """プロバイダーの表示"""
        icons = {
            'openai': '🤖',
            'anthropic': '🧠',
            'google': '🔍',
            'other': '🔧'
        }
        icon = icons.get(obj.provider, '❓')
        return format_html(
            '{} <strong>{}</strong>',
            icon,
            obj.get_provider_display()
        )
    provider_display.short_description = 'プロバイダー'
    provider_display.admin_order_field = 'provider'
    
    def usage_display(self, obj):
        """使用量の表示"""
        if obj.monthly_budget:
            percentage = (obj.current_usage / obj.monthly_budget) * 100
            color = '#28a745' if percentage < 70 else ('#ffc107' if percentage < 90 else '#dc3545')
            return format_html(
                '<span style="color: {};">${} / ${} ({}%)</span>',
                color,
                f'{obj.current_usage:.2f}',
                f'{obj.monthly_budget:.2f}',
                f'{percentage:.1f}'
            )
        return format_html('${}', f'{obj.current_usage:.2f}')
    usage_display.short_description = '使用量'
    
    def test_result_display(self, obj):
        """テスト結果表示エリア（新規作成時と既存レコードの両方に対応）"""
        from django.utils.safestring import mark_safe
        
        if obj.id:
            # 既存レコードの場合
            return mark_safe(
                f'<div id="test-result-{obj.id}" style="margin-top: 10px;">'
                f'<button type="button" onclick="testConnection(\'{obj.id}\')" '
                f'style="padding: 8px 16px; background: #417690; color: white; border: none; '
                f'border-radius: 4px; cursor: pointer;">接続テスト</button>'
                f'<div id="test-output-{obj.id}" style="margin-top: 10px;"></div>'
                f'</div>'
            )
        else:
            # 新規作成時: APIキーとプロバイダーを入力すればテスト可能
            return mark_safe(
                '<div id="test-result-new" style="margin-top: 10px;">'
                '<button type="button" onclick="testConnection(null)" '
                'style="padding: 8px 16px; background: #417690; color: white; border: none; '
                'border-radius: 4px; cursor: pointer;">接続テスト</button>'
                '<div style="margin-top: 5px; font-size: 12px; color: #666;">'
                '💡 APIキーとプロバイダーを入力してからテストしてください'
                '</div>'
                '<div id="test-output-new" style="margin-top: 10px;"></div>'
                '</div>'
            )
    test_result_display.short_description = '接続テスト'
    
    class Media:
        js = ('admin/js/provider_key_test.js',)
    
    def get_urls(self):
        """カスタムURLを追加"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'test-connection/',
                self.admin_site.admin_view(self.test_connection_view),
                name='spin_aiproviderkey_test_connection',
            ),
            path(
                'test-connection/<uuid:key_id>/',
                self.admin_site.admin_view(self.test_connection_view),
                name='spin_aiproviderkey_test_connection_with_id',
            ),
        ]
        return custom_urls + urls
    
    def test_connection_view(self, request, key_id=None):
        """接続テストビュー（新規作成時と既存レコードの両方に対応）"""
        if request.method == 'POST':
            try:
                import json
                from spin.services.ai_provider_factory import AIProviderFactory
                from spin.models import AIProviderKey
                
                # まずPOSTデータから取得を試みる（新規作成時）
                # JSONデータとフォームデータの両方から取得を試みる
                data = {}
                if request.body:
                    try:
                        data = json.loads(request.body)
                    except json.JSONDecodeError:
                        pass
                
                # 複数の方法で値を取得（JSON > POST > GETの順で優先）
                api_key = data.get('api_key') or request.POST.get('api_key') or request.GET.get('api_key')
                provider = data.get('provider') or request.POST.get('provider') or request.GET.get('provider')
                # JSONデータからkey_idも取得（URLパラメータより優先）
                json_key_id = data.get('key_id')
                if json_key_id:
                    key_id = json_key_id
                
                # デバッグ情報
                logger.info(f"Connection test request - key_id: {key_id}")
                logger.info(f"JSON data keys: {list(data.keys()) if data else 'empty'}")
                logger.info(f"POST data keys: {list(request.POST.keys()) if request.POST else 'empty'}")
                logger.info(f"Received - api_key: {'present (' + str(len(api_key)) + ' chars)' if api_key else 'missing'}, provider: {provider or 'missing'}")
                
                # key_idが指定されている場合、データベースに存在するか確認
                provider_key = None
                if key_id:
                    try:
                        provider_key = AIProviderKey.objects.get(id=key_id)
                        logger.info(f"Existing record found: key_id={key_id}, provider={provider_key.provider}")
                    except AIProviderKey.DoesNotExist:
                        logger.warning(f"Key ID not found in database: {key_id}, treating as new record")
                        provider_key = None
                
                # 新規作成時（key_idがない、または存在しない場合）はPOSTデータから取得
                if provider_key is None:
                    if not api_key or not provider:
                        error_details = []
                        if not api_key:
                            error_details.append('APIキーが取得できませんでした')
                        if not provider:
                            error_details.append('プロバイダーが取得できませんでした')
                        
                        logger.error(f"Missing required data: {', '.join(error_details)}")
                        return JsonResponse({
                            'success': False,
                            'message': 'APIキーとプロバイダーが必要です。\n' + '\n'.join(error_details)
                        })
                    
                    logger.info(f"New record test: provider={provider}, api_key={api_key[:20]}...")
                    
                    # 一時的なAIProviderKeyオブジェクトを作成
                    temp_provider_key = AIProviderKey(
                        api_key=api_key,
                        provider=provider
                    )
                    
                    # プロバイダーに応じたクライアントを作成してテスト
                    client = AIProviderFactory.create_client(temp_provider_key)
                    result = client.test_connection()
                    
                    logger.info(f"Connection test result: provider={provider}, success={result.get('success')}")
                    
                else:
                    # 既存レコードの場合でも、フォームから取得した値を使用（フォームが編集されている可能性があるため）
                    if api_key and provider:
                        # フォームから取得した値で一時オブジェクトを作成
                        logger.info(f"Existing record test (using form values): provider={provider}, api_key={api_key[:20]}...")
                        temp_provider_key = AIProviderKey(
                            api_key=api_key,
                            provider=provider
                        )
                        client = AIProviderFactory.create_client(temp_provider_key)
                    else:
                        # フォームから取得できない場合は、データベースの値を使用
                        logger.info(f"Existing record test (using DB values): provider={provider_key.provider}")
                        client = AIProviderFactory.create_client(provider_key)
                    result = client.test_connection()
                
                return JsonResponse(result)
                
            except ImportError as e:
                logger.error(f"Connection test import error: {e}")
                return JsonResponse({
                    'success': False,
                    'message': f'ライブラリがインストールされていません: {str(e)}'
                })
            except ValueError as e:
                logger.error(f"Connection test value error: {e}")
                return JsonResponse({
                    'success': False,
                    'message': f'プロバイダーエラー: {str(e)}'
                })
            except Exception as e:
                logger.error(f"Connection test error: {e}", exc_info=True)
                return JsonResponse({
                    'success': False,
                    'message': f'テストエラー: {str(e)}'
                })
        
        return JsonResponse({'success': False, 'message': 'Invalid request method'})


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    """AIモデル管理画面"""
    
    # 一覧表示
    list_display = ['display_name', 'provider_display', 'model_id', 'cost_display', 'api_key_status', 'recommended_display', 'is_active']
    list_filter = ['provider', 'is_active', 'supports_streaming', 'supports_function_calling', 'supports_vision']
    search_fields = ['model_id', 'display_name', 'description']
    ordering = ['provider', 'model_id']
    
    # ヘルプテキスト
    class Media:
        css = {
            'all': ('admin/css/aimodel_admin.css',)
        }
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'AIモデル一覧（マスターデータ）'
        return super().changelist_view(request, extra_context)
    
    # 詳細ページのフィールドセット
    fieldsets = (
        ('基本情報', {
            'fields': ('provider', 'model_id', 'display_name', 'description', 'is_active')
        }),
        ('性能指標', {
            'fields': ('context_window', 'max_output_tokens', 'supports_streaming', 'supports_function_calling', 'supports_vision')
        }),
        ('コスト情報', {
            'fields': ('input_cost_per_1m', 'output_cost_per_1m', 'estimated_cost_display')
        }),
        ('推奨用途', {
            'fields': ('recommended_for_generation', 'recommended_for_chat', 'recommended_for_scoring', 'recommended_for_analysis')
        }),
        ('日時情報', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'estimated_cost_display']
    
    def provider_display(self, obj):
        """プロバイダーの表示"""
        icons = {
            'openai': '🤖',
            'anthropic': '🧠',
            'google': '🔍',
            'other': '🔧'
        }
        icon = icons.get(obj.provider, '❓')
        return format_html('{} {}', icon, obj.get_provider_display())
    provider_display.short_description = 'プロバイダー'
    provider_display.admin_order_field = 'provider'
    
    def cost_display(self, obj):
        """コストの表示"""
        if obj.input_cost_per_1m and obj.output_cost_per_1m:
            return format_html(
                '入力: ${}/1M<br>出力: ${}/1M',
                f'{obj.input_cost_per_1m:.4f}',
                f'{obj.output_cost_per_1m:.4f}'
            )
        return '-'
    cost_display.short_description = 'コスト'
    
    def api_key_status(self, obj):
        """APIキーの登録状況"""
        # このプロバイダーのAPIキーが登録されているか確認
        api_keys = AIProviderKey.objects.filter(
            provider=obj.provider,
            is_active=True
        )
        
        key_count = api_keys.count()
        
        if key_count == 0:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">⚠️ APIキー未登録</span>'
            )
        elif key_count == 1:
            key = api_keys.first()
            return format_html(
                '<span style="color: #28a745;">✓ 利用可能</span><br>'
                '<span style="font-size: 11px; color: #666;">{}</span>',
                key.name
            )
        else:
            return format_html(
                '<span style="color: #28a745;">✓ 利用可能</span><br>'
                '<span style="font-size: 11px; color: #666;">{}個のキー</span>',
                key_count
            )
    api_key_status.short_description = 'APIキー'
    
    def recommended_display(self, obj):
        """推奨用途の表示"""
        badges = []
        if obj.recommended_for_generation:
            badges.append('<span style="background: #417690; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">SPIN生成</span>')
        if obj.recommended_for_chat:
            badges.append('<span style="background: #28a745; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">チャット</span>')
        if obj.recommended_for_scoring:
            badges.append('<span style="background: #ffc107; color: #333; padding: 2px 6px; border-radius: 3px; font-size: 11px;">スコアリング</span>')
        if obj.recommended_for_analysis:
            badges.append('<span style="background: #17a2b8; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">分析</span>')
        
        if badges:
            return format_html(' '.join(badges))
        return '-'
    recommended_display.short_description = '推奨用途'
    
    def estimated_cost_display(self, obj):
        """推定コストの表示（例: 1000入力/1000出力トークン）"""
        if obj.input_cost_per_1m and obj.output_cost_per_1m:
            cost = obj.get_estimated_cost(1000, 1000)
            return format_html('約 ${} (1K入力+1K出力)', f'{cost:.6f}')
        return '-'
    estimated_cost_display.short_description = '推定コスト例'

