from django.urls import path
from . import views

app_name = 'spin'

urlpatterns = [
    path('auth/register/', views.register_user, name='register_user'),
    path('auth/login/', views.login_user, name='login_user'),
    path('spin/generate/', views.generate_spin, name='generate_spin'),
    path('session/start/', views.start_session, name='start_session'),
    path('session/list/', views.list_sessions, name='list_sessions'),
    path('session/<uuid:id>/', views.get_session, name='get_session'),
    path('session/chat/', views.chat_session, name='chat_session'),
    path('session/finish/', views.finish_session, name='finish_session'),
    path('report/<int:id>/', views.get_report, name='get_report'),
]

