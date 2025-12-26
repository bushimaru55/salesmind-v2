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


def send_verification_email(user, token):
    """
    メール認証用のメールを送信
    
    Args:
        user: Userオブジェクト
        token: EmailVerificationTokenオブジェクト
    """
    try:
        from .models import UserEmail
        
        # UserEmail.is_verification_email=Trueのメールアドレスを取得
        verification_email = UserEmail.objects.filter(
            user=user,
            is_verification_email=True
        ).first()
        
        # UserEmailが存在しない場合は、既存のuser.emailを使用（後方互換性）
        recipient_email = verification_email.email if verification_email else (user.email or '')
        
        if not recipient_email:
            logger.error(f"No email address found for user {user.username}")
            return False
        
        verification_url = f"{settings.SITE_URL}/api/auth/verify-email/?token={token.token}"
        
        subject = "SalesMind - メールアドレスの認証"
        
        # HTMLメール本文
        html_message = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #132131;">SalesMind</h1>
                <h2>メールアドレスの認証</h2>
                <p>こんにちは、{user.username}さん</p>
                <p>SalesMindへのご登録ありがとうございます。</p>
                <p>以下のリンクをクリックして、メールアドレスを認証してください：</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="display: inline-block; padding: 12px 30px; background-color: #132131; color: #fff; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        メールアドレスを認証する
                    </a>
                </div>
                <p>または、以下のURLをブラウザにコピー＆ペーストしてください：</p>
                <p style="word-break: break-all; color: #666; font-size: 12px;">{verification_url}</p>
                <p style="color: #999; font-size: 12px; margin-top: 30px;">
                    このメールは、SalesMindへの登録リクエストにより送信されました。<br>
                    このリクエストをしていない場合は、このメールを無視してください。
                </p>
                <p style="color: #999; font-size: 12px;">
                    このリンクは24時間有効です。
                </p>
            </div>
        </body>
        </html>
        """
        
        # プレーンテキスト版
        plain_message = f"""
        SalesMind - メールアドレスの認証

        こんにちは、{user.username}さん

        SalesMindへのご登録ありがとうございます。

        以下のリンクをクリックして、メールアドレスを認証してください：

        {verification_url}

        このメールは、SalesMindへの登録リクエストにより送信されました。
        このリクエストをしていない場合は、このメールを無視してください。

        このリンクは24時間有効です。
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Verification email sent to {recipient_email} for user {user.username}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send verification email to user {user.username}: {e}", exc_info=True)
        return False


