from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from .models import SystemEmailAddress, EmailTemplate
import logging

logger = logging.getLogger(__name__)


@admin.register(SystemEmailAddress)
class SystemEmailAddressAdmin(admin.ModelAdmin):
    """システムメールアドレス管理画面"""
    list_display = [
        'email',
        'name',
        'purpose',
        'is_active_display',
        'is_default_display',
        'created_at'
    ]
    list_filter = ['purpose', 'is_active', 'is_default', 'created_at']
    search_fields = ['email', 'name', 'description']
    ordering = ['-is_default', 'purpose', 'email']
    
    fieldsets = (
        ('メールアドレス情報', {
            'fields': ('email', 'name', 'purpose')
        }),
        ('設定', {
            'fields': ('is_active', 'is_default', 'description')
        }),
        ('日時情報', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">●</span> 有効')
        return format_html('<span style="color: red;">○</span> 無効')
    is_active_display.short_description = '状態'
    
    def is_default_display(self, obj):
        if obj.is_default:
            return format_html('<span style="color: blue;">★ デフォルト</span>')
        return '-'
    is_default_display.short_description = 'デフォルト'


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    """メールテンプレート管理画面"""
    change_form_template = 'admin/email_management/emailtemplate/change_form.html'
    
    list_display = [
        'display_name',
        'name',
        'purpose',
        'from_email_display',
        'is_active_display',
        'updated_at'
    ]
    list_filter = ['purpose', 'is_active', 'created_at']
    search_fields = ['name', 'display_name', 'subject', 'description']
    ordering = ['purpose', 'name']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'display_name', 'purpose', 'is_active')
        }),
        ('送信設定', {
            'fields': ('from_email', 'subject')
        }),
        ('本文', {
            'fields': ('body_text', 'body_html')
        }),
        ('変数・説明', {
            'fields': ('available_variables', 'description'),
            'classes': ('collapse',)
        }),
        ('日時情報', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_urls(self):
        """カスタムURLを追加"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/test-send/',
                self.admin_site.admin_view(self.test_send_email_view),
                name='email_management_emailtemplate_test_send',
            ),
        ]
        return custom_urls + urls
    
    def test_send_email_view(self, request, object_id):
        """テストメール送信処理"""
        try:
            template = self.get_object(request, object_id)
            if template is None:
                messages.error(request, 'テンプレートが見つかりませんでした。')
                return redirect('admin:email_management_emailtemplate_changelist')
            
            if request.method == 'POST':
                test_email = request.POST.get('test_email', '').strip()
                
                if not test_email:
                    return JsonResponse({
                        'success': False,
                        'message': 'メールアドレスを入力してください。'
                    })
                
                # テンプレート変数のサンプルデータを準備
                context = {
                    'username': 'テストユーザー',
                    'email': test_email,
                    'verification_url': f'{settings.SITE_URL}/api/auth/verify-email/?token=test-token-sample',
                    'site_name': 'SalesMind',
                    'site_url': settings.SITE_URL,
                }
                
                try:
                    # テンプレートをレンダリング
                    subject, body_text, body_html = template.render(context)
                    
                    # 送信元メールアドレスを取得
                    if template.from_email and template.from_email.is_active:
                        from_email = f"{template.from_email.name} <{template.from_email.email}>"
                    else:
                        from spin.email_service import get_sender_email
                        from_email = get_sender_email(template.purpose if template.purpose != 'other' else 'default')
                    
                    # メール送信
                    from django.core.mail import send_mail
                    send_mail(
                        subject=subject,
                        message=body_text,
                        from_email=from_email,
                        recipient_list=[test_email],
                        html_message=body_html,
                        fail_silently=False,
                    )
                    
                    logger.info(f"Test email sent from template '{template.name}' to {test_email}")
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'テストメールを {test_email} に送信しました。'
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to send test email: {e}", exc_info=True)
                    return JsonResponse({
                        'success': False,
                        'message': f'メール送信に失敗しました: {str(e)}'
                    })
            
            return JsonResponse({
                'success': False,
                'message': 'POSTリクエストが必要です。'
            })
            
        except Exception as e:
            logger.error(f"Test send view error: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': f'エラーが発生しました: {str(e)}'
            })
    
    def from_email_display(self, obj):
        if obj.from_email:
            return format_html('{} &lt;{}&gt;', obj.from_email.name, obj.from_email.email)
        return format_html('<span style="color: #999;">（デフォルト）</span>')
    from_email_display.short_description = '送信元'
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">●</span> 有効')
        return format_html('<span style="color: red;">○</span> 無効')
    is_active_display.short_description = '状態'

