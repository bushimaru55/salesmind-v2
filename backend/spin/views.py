from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
import json
import uuid
import logging
from .models import Session, ChatMessage, Report
from .serializers import (
    SessionSerializer,
    ChatMessageSerializer,
    ReportSerializer,
    SpinGenerateSerializer,
)
from .services.openai_client import generate_spin as generate_spin_questions, generate_customer_response
from .services.scoring import score_conversation
from .exceptions import OpenAIAPIError, SessionNotFoundError, SessionFinishedError, NoConversationHistoryError

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """ユーザー登録エンドポイント"""
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    
    # バリデーション
    errors = {}
    if not username:
        errors['username'] = ["ユーザー名は必須です"]
    elif len(username) < 3:
        errors['username'] = ["ユーザー名は3文字以上で入力してください"]
    elif User.objects.filter(username=username).exists():
        errors['username'] = ["このユーザー名は既に使用されています"]
    
    if not password:
        errors['password'] = ["パスワードは必須です"]
    elif len(password) < 6:
        errors['password'] = ["パスワードは6文字以上で入力してください"]
    
    if email and User.objects.filter(email=email).exists():
        errors['email'] = ["このメールアドレスは既に使用されています"]
    
    if errors:
        return Response({
            "error": "Validation failed",
            "details": errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.create_user(
            username=username,
            email=email or '',
            password=password
        )
        # Tokenを自動生成
        token, _ = Token.objects.get_or_create(user=user)
        
        logger.info(f"User registered: {username}")
        
        return Response({
            "message": "ユーザー登録が完了しました",
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error(f"User registration failed: {e}", exc_info=True)
        return Response({
            "error": "ユーザー登録に失敗しました",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """ログインエンドポイント"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    # バリデーション
    if not username or not password:
        return Response({
            "error": "Validation failed",
            "details": {
                "username": ["ユーザー名は必須です"] if not username else [],
                "password": ["パスワードは必須です"] if not password else []
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 認証
    user = authenticate(username=username, password=password)
    
    if user is None:
        logger.warning(f"Login failed: invalid credentials for {username}")
        return Response({
            "error": "認証に失敗しました",
            "message": "ユーザー名またはパスワードが正しくありません"
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Tokenを取得または作成
    token, _ = Token.objects.get_or_create(user=user)
    
    logger.info(f"User logged in: {username}")
    
    return Response({
        "message": "ログインに成功しました",
        "token": token.key,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def generate_spin(request):
    """SPIN質問を生成するエンドポイント（認証不要）"""
    serializer = SpinGenerateSerializer(data=request.data)
    if serializer.is_valid():
        try:
            industry = serializer.validated_data['industry']
            value_prop = serializer.validated_data['value_proposition']
            persona = serializer.validated_data.get('customer_persona')
            pain = serializer.validated_data.get('customer_pain')
            
            # OpenAI API呼び出し
            response_text = generate_spin_questions(industry, value_prop, persona, pain)
            
            # レスポンスをパース（JSON形式を想定）
            try:
                questions = json.loads(response_text)
            except json.JSONDecodeError:
                # JSON形式でない場合は、エラーとして返す
                return Response({
                    "error": "Failed to parse OpenAI response",
                    "message": "Response is not valid JSON format"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({"questions": questions}, status=status.HTTP_200_OK)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            return Response({
                "error": "Failed to parse OpenAI response",
                "message": "OpenAI APIからのレスポンスがJSON形式ではありません"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Failed to generate SPIN questions: {e}", exc_info=True)
            raise OpenAIAPIError(f"SPIN質問生成に失敗しました: {str(e)}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_session(request):
    """セッションを開始するエンドポイント"""
    serializer = SessionSerializer(data=request.data)
    if serializer.is_valid():
        session = serializer.save(user=request.user, status='active')
        logger.info(f"Session started: {session.id} by user {request.user.username}")
        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_session(request):
    """商談セッション中にAI顧客と対話するエンドポイント"""
    session_id = request.data.get('session_id')
    message = request.data.get('message')
    
    # バリデーション
    errors = {}
    if not session_id:
        errors['session_id'] = ["このフィールドは必須です"]
    elif session_id and not isinstance(session_id, str) and not isinstance(session_id, uuid.UUID):
        try:
            uuid.UUID(str(session_id))
        except ValueError:
            errors['session_id'] = ["有効なUUID形式で入力してください"]
    
    if not message:
        errors['message'] = ["このフィールドは必須です"]
    elif message and len(message.strip()) < 1:
        errors['message'] = ["メッセージは1文字以上で入力してください"]
    elif message and len(message.strip()) > 1000:
        errors['message'] = ["メッセージは1000文字以内で入力してください"]
    
    if errors:
        return Response({
            "error": "Validation failed",
            "details": errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        session = Session.objects.get(id=session_id, user=request.user)
    except Session.DoesNotExist:
        logger.warning(f"Session not found: {session_id}, user: {request.user.id}")
        raise SessionNotFoundError(f"セッションが見つかりません: {session_id}")
    
    if session.status != 'active':
        logger.warning(f"Session already finished: {session_id}")
        raise SessionFinishedError(f"セッションは既に終了しています: {session_id}")
    
    # 営業担当者のメッセージを保存
    messages = session.messages.all()
    sequence = messages.count() + 1
    
    salesperson_msg = ChatMessage.objects.create(
        session=session,
        role='salesperson',
        message=message,
        sequence=sequence
    )
    
    # AI顧客の応答を生成
    try:
        conversation_history = list(messages) + [salesperson_msg]
        customer_response = generate_customer_response(session, conversation_history)
        
        # AI顧客のメッセージを保存
        customer_msg = ChatMessage.objects.create(
            session=session,
            role='customer',
            message=customer_response,
            sequence=sequence + 1
        )
        
        # 最新の会話履歴を取得
        all_messages = list(session.messages.all().order_by('sequence'))
        conversation = [
            {
                "role": msg.role,
                "message": msg.message,
                "created_at": msg.created_at.isoformat()
            }
            for msg in all_messages
        ]
        
        return Response({
            "session_id": str(session_id),
            "conversation": conversation
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Failed to generate customer response: {e}", exc_info=True)
        raise OpenAIAPIError(f"AI顧客の応答生成に失敗しました: {str(e)}")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def finish_session(request):
    """セッションを終了し、スコアリングを実行するエンドポイント"""
    session_id = request.data.get('session_id')
    
    # バリデーション
    if not session_id:
        return Response({
            "error": "Validation failed",
            "details": {
                "session_id": ["このフィールドは必須です"]
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # UUID形式の検証
    if not isinstance(session_id, str) and not isinstance(session_id, uuid.UUID):
        try:
            uuid.UUID(str(session_id))
        except ValueError:
            return Response({
                "error": "Validation failed",
                "details": {
                    "session_id": ["有効なUUID形式で入力してください"]
                }
            }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        session = Session.objects.get(id=session_id, user=request.user)
    except Session.DoesNotExist:
        logger.warning(f"Session not found: {session_id}, user: {request.user.id}")
        raise SessionNotFoundError(f"セッションが見つかりません: {session_id}")
    
    if session.status == 'finished':
        logger.warning(f"Session already finished: {session_id}")
        raise SessionFinishedError("セッションは既に終了しています")
    
    # 会話履歴を取得
    conversation_history = list(session.messages.all().order_by('sequence'))
    
    if not conversation_history:
        logger.warning(f"No conversation history for session: {session_id}")
        raise NoConversationHistoryError("会話履歴がありません。まずチャットを開始してください")
    
    # スコアリングを実行
    try:
        scoring_result = score_conversation(session, conversation_history)
        scores_data = json.loads(scoring_result)
        
        # スコアリング結果を保存
        report = Report.objects.create(
            session=session,
            spin_scores={
                "situation": scores_data.get("situation", 0),
                "problem": scores_data.get("problem", 0),
                "implication": scores_data.get("implication", 0),
                "need": scores_data.get("need", 0),
                "total": scores_data.get("total", 0)
            },
            feedback=scores_data.get("feedback", ""),
            next_actions=scores_data.get("next_actions", ""),
            scoring_details=scores_data.get("scoring_details", {})
        )
        
        # セッションを終了状態に更新
        session.status = 'finished'
        session.finished_at = timezone.now()
        session.save()
        
        logger.info(f"Session finished and scored: {session_id}, total_score: {report.spin_scores.get('total', 0)}")
        return Response({
            "session_id": str(session_id),
            "report_id": report.id,
            "status": "finished",
            "finished_at": session.finished_at.isoformat(),
            "spin_scores": report.spin_scores,
            "feedback": report.feedback,
            "next_actions": report.next_actions
        }, status=status.HTTP_200_OK)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse scoring result: {e}")
        raise OpenAIAPIError("スコアリング結果の解析に失敗しました")
    except Exception as e:
        logger.error(f"Failed to generate score: {e}", exc_info=True)
        raise OpenAIAPIError(f"スコアリングに失敗しました: {str(e)}")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_sessions(request):
    """ユーザーのセッション一覧を取得するエンドポイント"""
    sessions = Session.objects.filter(user=request.user).order_by('-created_at')
    
    # ページネーション（オプション）
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size
    
    sessions_page = sessions[start:end]
    
    serializer = SessionSerializer(sessions_page, many=True)
    return Response({
        "count": sessions.count(),
        "page": page,
        "page_size": page_size,
        "results": serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_session(request, id):
    """セッション詳細を取得するエンドポイント"""
    try:
        session = Session.objects.get(id=id, user=request.user)
    except Session.DoesNotExist:
        logger.warning(f"Session not found: {id}, user: {request.user.id}")
        raise SessionNotFoundError(f"セッションが見つかりません: {id}")
    
    serializer = SessionSerializer(session)
    
    # 会話履歴も含める
    messages = session.messages.all().order_by('sequence')
    messages_data = ChatMessageSerializer(messages, many=True).data
    
    response_data = serializer.data
    response_data['messages'] = messages_data
    
    # レポートがある場合は含める
    try:
        report = session.report
        response_data['report'] = ReportSerializer(report).data
    except Report.DoesNotExist:
        response_data['report'] = None
    
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_report(request, id):
    """レポート詳細を取得するエンドポイント"""
    report = get_object_or_404(Report, id=id)
    # 他ユーザーのレポートへのアクセスを防止
    if report.session.user != request.user:
        return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
    return Response(ReportSerializer(report).data, status=status.HTTP_200_OK)
