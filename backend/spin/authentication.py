"""
カスタム認証クラス
"""
from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    CSRF検証をスキップするSessionAuthentication
    
    フロントエンドからのAPIリクエストではCSRFトークンを使用せず、
    Token認証を使用するため、SessionAuthenticationのCSRF検証を無効化します。
    """
    def enforce_csrf(self, request):
        return  # CSRF検証をスキップ

