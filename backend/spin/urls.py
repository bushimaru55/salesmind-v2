from django.urls import path
from . import views

app_name = 'spin'

urlpatterns = [
    # ヘルスチェック
    path('health/', views.health, name='health'),

    # 認証
    path('auth/register/', views.register_user, name='register_user'),
    path('auth/login/', views.login_user, name='login_user'),

    # SPIN質問生成
    path('spin/generate/', views.generate_spin, name='generate_spin'),

    # セッション関連
    path('session/start/', views.start_session, name='start_session'),
    path('session/list/', views.list_sessions, name='list_sessions'),
    path('session/<uuid:id>/', views.get_session, name='get_session'),
    path('session/chat/', views.chat_session, name='chat_session'),
    path('session/chat/stream/', views.chat_session_stream, name='chat_session_stream'),
    path('session/finish/', views.finish_session, name='finish_session'),

    # レポート
    path('report/<int:id>/', views.get_report, name='get_report'),

    # 企業スクレイピング関連
    path('company/scrape/', views.scrape_company, name='scrape_company'),
    path('company/scrape-from-sitemap/', views.scrape_from_sitemap, name='scrape_from_sitemap'),
    path('company/analyze/', views.analyze_company, name='analyze_company'),

    # ランキング関連
    path('ranking/simple/', views.get_simple_ranking, name='get_simple_ranking'),
    path('ranking/detailed/', views.get_detailed_ranking, name='get_detailed_ranking'),

    # 音声変換
    path('speech/transcribe/', views.transcribe_speech, name='transcribe_speech'),
]

