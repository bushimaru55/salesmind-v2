"""
カスタム例外クラス
"""
from rest_framework import status
from rest_framework.exceptions import APIException


class OpenAIAPIError(APIException):
    """OpenAI API呼び出しエラー"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "OpenAI API呼び出しに失敗しました"
    default_code = "openai_api_error"


class SessionNotFoundError(APIException):
    """セッションが見つからないエラー"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "セッションが見つかりません"
    default_code = "session_not_found"


class SessionFinishedError(APIException):
    """セッションが既に終了しているエラー"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "セッションは既に終了しています"
    default_code = "session_finished"


class NoConversationHistoryError(APIException):
    """会話履歴がないエラー"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "会話履歴がありません"
    default_code = "no_conversation_history"

