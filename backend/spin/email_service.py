"""
メール送信サービス
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def get_sender_email(purpose='default'):
    """
    用途に応じた送信元メールアドレスを取得
    
    Args:
        purpose (str): メール送信の用途
            - 'default': デフォルト
            - 'registration': 会員登録確認
            - 'password_reset': パスワードリセット
            - 'notification': 通知
            - 'support': サポート
            - 'marketing': マーケティング
            - 'system': システム通知
    
    Returns:
        str: 送信元メールアドレス（形式: "表示名 <email@domain.com>"）
    """
    try:
        from .models import SystemEmailAddress
        
        # 指定された用途で有効なメールアドレスを取得
        sender = SystemEmailAddress.objects.get(
            purpose=purpose,
            is_active=True
        )
        return f"{sender.name} <{sender.email}>"
    except SystemEmailAddress.DoesNotExist:
        # 見つからない場合はデフォルトを取得
        try:
            from .models import SystemEmailAddress
            default = SystemEmailAddress.objects.get(
                is_default=True,
                is_active=True
            )
            return f"{default.name} <{default.email}>"
        except SystemEmailAddress.DoesNotExist:
            # それでも見つからない場合は設定ファイルのデフォルトを使用
            return settings.DEFAULT_FROM_EMAIL
    except Exception as e:
        logger.error(f"Error getting sender email for purpose '{purpose}': {e}")
        return settings.DEFAULT_FROM_EMAIL


def get_email_template(template_name):
    """
    テンプレート名からEmailTemplateを取得
    
    Args:
        template_name (str): テンプレート名（例: 'registration_email'）
    
    Returns:
        EmailTemplate or None
    """
    try:
        from .models import EmailTemplate
        return EmailTemplate.objects.get(
            name=template_name,
            is_active=True
        )
    except EmailTemplate.DoesNotExist:
        logger.warning(f"Email template '{template_name}' not found or inactive")
        return None


def send_email_from_template(template_name, recipient_email, context, purpose='default'):
    """
    テンプレートを使用してメールを送信
    
    Args:
        template_name (str): テンプレート名
        recipient_email (str): 受信者メールアドレス
        context (dict): テンプレート変数の辞書
        purpose (str): メール送信の用途（送信元選択用）
    
    Returns:
        bool: 送信成功時True
    """
    try:
        template = get_email_template(template_name)
        
        if template:
            # テンプレートで指定された送信元を使用
            if template.from_email and template.from_email.is_active:
                from_email = f"{template.from_email.name} <{template.from_email.email}>"
            else:
                # テンプレートに送信元が設定されていない場合は用途から取得
                from_email = get_sender_email(purpose)
            
            # テンプレートをレンダリング
            subject, body_text, body_html = template.render(context)
        else:
            # テンプレートが見つからない場合はデフォルトの動作
            logger.warning(f"Using fallback for template '{template_name}'")
            from_email = get_sender_email(purpose)
            subject = "SalesMind"
            body_text = "メールテンプレートが設定されていません。"
            body_html = None
        
        # メール送信
        send_mail(
            subject=subject,
            message=body_text,
            from_email=from_email,
            recipient_list=[recipient_email],
            html_message=body_html,
            fail_silently=False,
        )
        
        logger.info(f"Email sent from template '{template_name}' to {recipient_email} from {from_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email from template '{template_name}': {e}", exc_info=True)
        return False


def send_verification_email(user, token):
    """
    メール認証用のメールを送信（テンプレート使用版）
    
    Args:
        user: Userオブジェクト
        token: EmailVerificationTokenオブジェクト
    """
    try:
        from .models import UserEmail
        
        # 受信者メールアドレスを取得
        verification_email = UserEmail.objects.filter(
            user=user,
            is_verification_email=True
        ).first()
        
        recipient_email = verification_email.email if verification_email else (user.email or '')
        
        if not recipient_email:
            logger.error(f"No email address found for user {user.username}")
            return False
        
        # 認証URLを生成
        verification_url = f"{settings.SITE_URL}/api/auth/verify-email/?token={token.token}"
        
        # テンプレート変数を準備
        context = {
            'username': user.username,
            'email': recipient_email,
            'verification_url': verification_url,
            'site_name': 'SalesMind',
            'site_url': settings.SITE_URL,
        }
        
        # テンプレートからメール送信
        return send_email_from_template(
            template_name='registration_email',
            recipient_email=recipient_email,
            context=context,
            purpose='registration'
        )
        
    except Exception as e:
        logger.error(f"Failed to send verification email to user {user.username}: {e}", exc_info=True)
        return False


