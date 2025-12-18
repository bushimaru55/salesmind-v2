from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.db.models import Avg, Max, Count, Q
from django.db.models.functions import Coalesce
from django.db import transaction
import json
import uuid
import logging
from .models import Session, ChatMessage, Report, Company, CompanyAnalysis
from .serializers import (
    SessionSerializer,
    ChatMessageSerializer,
    ReportSerializer,
    SpinGenerateSerializer,
    CompanySerializer,
    CompanyScrapeSerializer,
    CompanySitemapSerializer,
    CompanyAnalysisSerializer,
    CompanyAnalyzeSerializer,
)
from .services.openai_client import generate_spin as generate_spin_questions, generate_customer_response
from .services.closing_helper import (
    should_trigger_closing, 
    generate_closing_proposal, 
    check_need_payoff_complete,
    check_loss_candidate,
    check_loss_confirmed,
    generate_loss_response,
    LOSS_REASONS
)
from .services.temperature_score import calculate_temperature_score
from .services.scoring import score_conversation
from .services.scraper import scrape_company_info, scrape_multiple_urls
from .services.sitemap_parser import parse_sitemap_from_file, parse_sitemap_from_url, parse_sitemap_index
from .services.company_analyzer import analyze_spin_suitability
from .services.conversation_analysis import analyze_sales_message
from .exceptions import OpenAIAPIError, SessionNotFoundError, SessionFinishedError, NoConversationHistoryError

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    """
    シンプルなヘルスチェックエンドポイント。

    - URL: /api/health
    - Method: GET
    - Response: {"status": "ok"}
    """
    return Response({"status": "ok"}, status=status.HTTP_200_OK)


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
    serializer = SessionSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        session = serializer.save(user=request.user, status='active')
        
        # 詳細診断モードの場合、初期成功率を50%に設定
        if session.mode == 'detailed':
            session.success_probability = 50
            session.save()
            logger.info(f"詳細診断セッション開始: Session {session.id}, 初期成功率=50%")
        
        logger.info(f"Session started: {session.id}, mode={session.mode}, user={request.user.username}")
        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)
    logger.warning(f"Session start validation failed: {serializer.errors}")
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
    
    # 無限ループ防止: 同じメッセージが連続しないようにチェック
    last_message = session.messages.filter(role='salesperson').order_by('-sequence').first()
    if last_message and last_message.message.strip() == message.strip():
        return Response({
            "error": "Validation failed",
            "details": {
                "message": ["同じメッセージを連続して送信することはできません"]
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
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
        
        # クロージングスタイルを判定（営業メッセージから）
        closing_style = None
        message_lower = message.lower()
        
        # 選択肢型クロージング（例：「デモと無料体験、どちらで進めましょう？」）
        option_keywords = ['どちら', 'どっち', 'どれ', 'どちらで', 'どちらが', 'どちらを']
        if any(keyword in message_lower for keyword in option_keywords):
            closing_style = "option_based"
        # 一気に押すクロージング（例：「ぜひ導入してください」）
        elif any(keyword in message_lower for keyword in ['ぜひ', '必ず', '絶対', '今すぐ', 'すぐに']):
            closing_style = "one_shot_push"
        
        # 顧客温度スコアを計算（SPIN順序ペナルティは後で更新されるため、初期値は0）
        temperature_result = calculate_temperature_score(
            customer_response, 
            use_llm=True,
            spin_penalty=0.0,  # 後で更新される
            closing_style=closing_style
        )
        
        # AI顧客のメッセージを保存
        customer_msg = ChatMessage.objects.create(
            session=session,
            role='customer',
            message=customer_response,
            sequence=sequence + 1,
            temperature_score=temperature_result.get('temperature'),
            temperature_details={
                'sentiment': temperature_result.get('sentiment'),
                'sentiment_score': temperature_result.get('sentiment_score'),
                'buying_signal': temperature_result.get('buying_signal'),
                'cognitive_load': temperature_result.get('cognitive_load'),
                'engagement': temperature_result.get('engagement'),
                'question_score': temperature_result.get('question_score'),
            }
        )
        
        # 詳細診断モードかつ企業情報がある場合、成功率を分析・更新
        success_probability = session.success_probability
        success_delta = 0
        analysis_reason = None
        current_spin_stage = None
        message_spin_type = None
        step_appropriateness = None
        stage_evaluation = 'unknown'
        system_notes = None
        stage_labels = {
            'S': '状況確認',
            'P': '課題顕在化',
            'I': '示唆',
            'N': '解決メリット',
        }
        stage_order = {'S': 0, 'P': 1, 'I': 2, 'N': 3}
        current_stage_value = session.current_spin_stage or 'S'
         
        if session.mode == 'detailed' and session.company:
            try:
                # 営業メッセージを分析
                analysis_result = analyze_sales_message(session, conversation_history, message)
                success_delta = analysis_result.get('success_delta', 0)
                analysis_reason = analysis_result.get('reason', '')
                current_spin_stage = analysis_result.get('current_spin_stage')
                message_spin_type = analysis_result.get('message_spin_type')
                step_appropriateness = analysis_result.get('step_appropriateness')
                
                # SPIN順序ペナルティの緩和ロジック
                adjusted_delta = success_delta
                spin_order_penalty = 0.0
                
                if message_spin_type in stage_order:
                    diff = stage_order[message_spin_type] - stage_order.get(current_stage_value, 0)
                    if diff == 0:
                        stage_evaluation = 'repeat'
                        adjusted_delta = max(min(success_delta, 1), -1)
                    elif diff == 1:
                        stage_evaluation = 'advance'
                        adjusted_delta = max(success_delta, 2)
                    elif diff > 1:
                        stage_evaluation = 'jump'
                        # 順序違反ペナルティを最大30%に制限
                        original_penalty = min(success_delta, -3)
                        spin_order_penalty = original_penalty * 0.3
                        adjusted_delta = spin_order_penalty
                    elif diff < 0:
                        stage_evaluation = 'regression'
                        # 順序違反ペナルティを最大30%に制限
                        original_penalty = min(success_delta, -2)
                        spin_order_penalty = original_penalty * 0.3
                        adjusted_delta = spin_order_penalty
                else:
                    stage_evaluation = 'unknown'
                    adjusted_delta = min(success_delta, 0)
                
                # 顧客の前向き反応があれば、順序ペナルティをさらに軽減（50%）
                # 顧客メッセージから前向き反応をチェック
                customer_response_lower = customer_response.lower()
                positive_keywords = ['興味', '詳しく', 'デモ', '体験', '導入', '価値', '検討', 'メリット']
                has_positive_response = any(keyword in customer_response_lower for keyword in positive_keywords)
                
                if has_positive_response and spin_order_penalty < 0:
                    spin_order_penalty = spin_order_penalty * 0.5
                    adjusted_delta = spin_order_penalty

                adjusted_delta = max(-5, min(5, adjusted_delta))
                success_delta = adjusted_delta
                
                if message_spin_type in stage_order:
                    stage_name = stage_labels.get(message_spin_type, message_spin_type)
                else:
                    stage_name = '判定不能'
                eval_map = {
                    'advance': '段階が前進しました',
                    'repeat': '同じ段階での深掘りです',
                    'jump': '段階を飛び越えています',
                    'regression': '段階が逆戻りしています',
                    'unknown': '段階を判定できません',
                }
                system_notes = eval_map.get(stage_evaluation, '')
                if analysis_reason:
                    analysis_reason = f"{analysis_reason} / システム判定: {stage_name}・{system_notes}"
                else:
                    analysis_reason = f"システム判定: {stage_name}・{system_notes}"
                
                # 成功率を更新（0-100の範囲でクリップ）
                new_probability = session.success_probability + success_delta
                success_probability = max(0, min(100, new_probability))
                
                # セッションの成功率を更新
                session.success_probability = success_probability
                session.last_analysis_reason = analysis_reason
                
                # SPIN段階の更新とconversation_phaseの更新
                if message_spin_type in stage_order:
                    # 段階が前進、または同段階であれば更新
                    if stage_evaluation in ['advance', 'repeat']:
                        session.current_spin_stage = message_spin_type
                        # conversation_phaseも更新
                        phase_map = {
                            'S': 'SPIN_S',
                            'P': 'SPIN_P',
                            'I': 'SPIN_I',
                            'N': 'SPIN_N'
                        }
                        if message_spin_type in phase_map:
                            session.conversation_phase = phase_map[message_spin_type]
                
                # 失注候補をチェック
                updated_history = list(session.messages.all().order_by('sequence')) + [salesperson_msg]
                loss_reason = check_loss_candidate(session, updated_history)
                
                if loss_reason:
                    # 失注候補に遷移
                    if session.conversation_phase != 'LOSS_CANDIDATE':
                        session.conversation_phase = 'LOSS_CANDIDATE'
                        session.loss_reason = loss_reason
                        logger.info(f"失注候補に遷移: Session {session.id}, reason={loss_reason}")
                elif should_trigger_closing(session, updated_history):
                    # Need-Payoff完了をチェックしてCLOSING_READYに遷移
                    session.conversation_phase = 'CLOSING_READY'
                    logger.info(f"クロージング準備完了: Session {session.id}")
                
                session.save()
                
                # 営業メッセージに分析結果を保存
                salesperson_msg.success_delta = success_delta
                summary_lines = []
                if analysis_reason:
                    summary_lines.append(analysis_reason)
                if step_appropriateness:
                    summary_lines.append(f"ステップ適切性: {step_appropriateness}")
                if message_spin_type:
                    summary_lines.append(f"今回の発言: {message_spin_type}")
                if stage_evaluation:
                    summary_lines.append(f"段階評価: {stage_evaluation}")
                salesperson_msg.analysis_summary = "\n".join(summary_lines) if summary_lines else None
                salesperson_msg.spin_stage = message_spin_type if message_spin_type in stage_order else None
                salesperson_msg.stage_evaluation = stage_evaluation
                salesperson_msg.system_notes = system_notes
                salesperson_msg.save()
                
                # 温度スコアを再計算（SPIN順序ペナルティを含める）
                # SPIN順序違反があった場合のペナルティを計算
                spin_penalty_for_temp = 0.0
                if stage_evaluation in ['jump', 'regression']:
                    # 順序違反ペナルティを最大30%に制限
                    if stage_evaluation == 'jump':
                        original_penalty = -3.0
                    else:  # regression
                        original_penalty = -2.0
                    spin_penalty_for_temp = original_penalty * 0.3
                    
                    # 顧客の前向き反応があれば、順序ペナルティをさらに軽減（50%）
                    customer_response_lower = customer_response.lower()
                    positive_keywords = ['興味', '詳しく', 'デモ', '体験', '導入', '価値', '検討', 'メリット']
                    has_positive_response = any(keyword in customer_response_lower for keyword in positive_keywords)
                    if has_positive_response:
                        spin_penalty_for_temp = spin_penalty_for_temp * 0.5
                
                # 温度スコアを再計算
                temperature_result = calculate_temperature_score(
                    customer_response,
                    use_llm=True,
                    spin_penalty=spin_penalty_for_temp,
                    closing_style=closing_style
                )
                
                # 温度スコアを更新
                customer_msg.temperature_score = temperature_result.get('temperature')
                customer_msg.temperature_details = {
                    'sentiment': temperature_result.get('sentiment'),
                    'sentiment_score': temperature_result.get('sentiment_score'),
                    'buying_signal': temperature_result.get('buying_signal'),
                    'cognitive_load': temperature_result.get('cognitive_load'),
                    'engagement': temperature_result.get('engagement'),
                    'question_score': temperature_result.get('question_score'),
                    'positive_response': temperature_result.get('positive_response'),
                    'spin_penalty': temperature_result.get('spin_penalty'),
                    'closing_bonus': temperature_result.get('closing_bonus'),
                }
                customer_msg.save()
                
                logger.info(
                    "成功率更新: Session %s, Delta=%s, New=%s%%, stage=%s, message=%s, step=%s, eval=%s, temp=%s",
                    session.id,
                    success_delta,
                    success_probability,
                    current_spin_stage,
                    message_spin_type,
                    step_appropriateness,
                    stage_evaluation,
                    temperature_result.get('temperature'),
                )
            except Exception as e:
                logger.warning(f"成功率分析に失敗しました: {e}", exc_info=True)
                # 分析に失敗した場合は成功率は変更しない
                success_probability = session.success_probability
        
        # 失注確定のチェック
        loss_response = None
        updated_history_for_loss = list(session.messages.all().order_by('sequence'))
        if session.conversation_phase == 'LOSS_CANDIDATE':
            loss_reason = session.loss_reason or 'NO_URGENCY'
            if check_loss_confirmed(session, updated_history_for_loss, loss_reason):
                session.conversation_phase = 'LOSS_CONFIRMED'
                session.save()
                loss_response = generate_loss_response(loss_reason)
                logger.info(f"失注確定: Session {session.id}, reason={loss_reason}")
        
        # クロージング提案の生成（CLOSING_READY状態の場合）
        closing_proposal = None
        if session.conversation_phase == 'CLOSING_READY' and not loss_response:
            try:
                updated_history = list(session.messages.all().order_by('sequence'))
                closing_proposal = generate_closing_proposal(session, updated_history)
                logger.info(f"クロージング提案を生成: Session {session.id}, type={closing_proposal.get('action_type')}")
            except Exception as e:
                logger.warning(f"クロージング提案生成に失敗: {e}", exc_info=True)
        
        # 無限ループ防止: 会話が長すぎる場合（25回以上）はクロージングまたは失注を強制
        all_messages_count = session.messages.count()
        if all_messages_count >= 25 and session.conversation_phase not in ['CLOSING_READY', 'CLOSING_ACTION', 'LOSS_CANDIDATE', 'LOSS_CONFIRMED']:
            # 成功率が低い場合は失注、高い場合はクロージング
            if session.success_probability <= 40:
                session.conversation_phase = 'LOSS_CANDIDATE'
                session.loss_reason = 'NO_URGENCY'
                session.save()
                logger.info(f"会話が長すぎるため失注候補に強制: Session {session.id}, メッセージ数={all_messages_count}")
            else:
                session.conversation_phase = 'CLOSING_READY'
                session.save()
                if not closing_proposal:
                    closing_proposal = generate_closing_proposal(session, list(session.messages.all().order_by('sequence')))
                logger.info(f"会話が長すぎるためクロージングを強制: Session {session.id}, メッセージ数={all_messages_count}")
        
        # 最新の会話履歴を取得
        all_messages = list(session.messages.all().order_by('sequence'))
        conversation = []
        temperature_history = []  # 温度スコアの履歴
        
        for msg in all_messages:
            msg_data = {
                "role": msg.role,
                "message": msg.message,
                "created_at": msg.created_at.isoformat()
            }
            
            # 顧客メッセージの場合、温度スコアを追加
            if msg.role == 'customer' and msg.temperature_score is not None:
                msg_data["temperature_score"] = msg.temperature_score
                msg_data["temperature_details"] = msg.temperature_details or {}
                temperature_history.append({
                    "sequence": msg.sequence,
                    "temperature": msg.temperature_score,
                    "created_at": msg.created_at.isoformat()
                })
            
            conversation.append(msg_data)
        
        # レスポンスデータを構築
        response_data = {
            "session_id": str(session_id),
            "conversation": conversation,
            "conversation_phase": session.conversation_phase,
            "temperature_history": temperature_history,
        }
        
        # 最新の温度スコアを追加
        if customer_msg.temperature_score is not None:
            response_data["current_temperature"] = customer_msg.temperature_score
            response_data["temperature_details"] = customer_msg.temperature_details or {}
        
        # 失注確定の場合、失注情報を追加
        if loss_response:
            response_data["loss_response"] = loss_response
            response_data["should_end_session"] = True  # セッション終了を促すフラグ
        
        # クロージング提案がある場合は追加
        if closing_proposal:
            response_data["closing_proposal"] = closing_proposal
        
        # 詳細診断モードの場合、成功率情報を追加
        if session.mode == 'detailed':
            response_data["success_probability"] = success_probability
            response_data["success_delta"] = success_delta
            response_data["current_spin_stage"] = current_spin_stage
            response_data["message_spin_type"] = message_spin_type
            response_data["step_appropriateness"] = step_appropriateness
            response_data["stage_evaluation"] = stage_evaluation
            if analysis_reason:
                response_data["analysis_reason"] = analysis_reason
            if system_notes:
                response_data["system_notes"] = system_notes
            response_data["session_spin_stage"] = session.current_spin_stage
        
        return Response(response_data, status=status.HTTP_200_OK)
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
        
        # トランザクション内でデータを確実に保存
        with transaction.atomic():
            # 新しい5要素スコアリングに対応
            # 後方互換性のため、SPIN要素も含める
            spin_scores = {
                "total": scores_data.get("total", 0),
                # 新しい5要素スコア
                "exploration": scores_data.get("exploration", 0),
                "implication": scores_data.get("implication", 0),
                "value_proposition": scores_data.get("value_proposition", 0),
                "customer_response": scores_data.get("customer_response", 0),
                "advancement": scores_data.get("advancement", 0),
                # 後方互換性のためSPIN要素も含める
                "situation": scores_data.get("situation", scores_data.get("exploration", 0) // 2),
                "problem": scores_data.get("problem", scores_data.get("exploration", 0) // 2),
                "implication_legacy": scores_data.get("implication", 0),
                "need": scores_data.get("need", scores_data.get("value_proposition", 0))
            }
            
            # スコアリング結果を保存
            report = Report.objects.create(
                session=session,
                spin_scores=spin_scores,
                feedback=scores_data.get("feedback", ""),
                next_actions=scores_data.get("next_actions", ""),
                scoring_details=scores_data.get("scoring_details", {})
            )
            
            # セッションを終了状態に更新
            session.status = 'finished'
            session.finished_at = timezone.now()
            session.save()
            
            logger.info(f"Session finished and scored: {session_id}, total_score: {report.spin_scores.get('total', 0)}, report_id: {report.id}")
        
        # データが確実に保存されたことを確認
        saved_report = Report.objects.get(id=report.id)
        saved_session = Session.objects.get(id=session.id)
        
        if saved_session.status != 'finished':
            logger.error(f"Session status not saved correctly: {session_id}")
            raise Exception("セッション状態の保存に失敗しました")
        
        if not saved_report:
            logger.error(f"Report not saved correctly: {session_id}")
            raise Exception("レポートの保存に失敗しました")
        
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def scrape_company(request):
    """企業URLから情報をスクレイピングするエンドポイント（単一URL）"""
    serializer = CompanyScrapeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        url = serializer.validated_data['url']
        value_proposition = serializer.validated_data.get('value_proposition')
        
        logger.info(f"企業スクレイピングを開始: URL={url}, User={request.user.username}")
        
        # スクレイピング実行
        company_info = scrape_company_info(url)
        
        # Companyモデルに保存
        company = Company.objects.create(
            user=request.user,
            source_url=url,
            scrape_source='url',
            company_name=company_info.get('company_name', 'Unknown'),
            industry=company_info.get('industry'),
            business_description=company_info.get('business_description'),
            location=company_info.get('location'),
            employee_count=company_info.get('employee_count'),
            established_year=company_info.get('established_year'),
            scraped_data=company_info
        )
        
        logger.info(f"企業情報を保存しました: Company ID={company.id}")
        
        # 価値提案がある場合、分析も実行
        analysis_result = None
        if value_proposition:
            try:
                analysis_result = analyze_spin_suitability(company_info, value_proposition)
                company_analysis = CompanyAnalysis.objects.create(
                    company=company,
                    user=request.user,
                    value_proposition=value_proposition,
                    spin_suitability=analysis_result.get('spin_suitability', {}),
                    recommendations=analysis_result.get('recommendations', {})
                )
                logger.info(f"企業分析を保存しました: Analysis ID={company_analysis.id}")
            except Exception as e:
                logger.warning(f"企業分析の実行に失敗しました: {e}", exc_info=True)
        
        response_data = CompanySerializer(company).data
        if analysis_result:
            response_data['analysis'] = analysis_result
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    except ValueError as e:
        logger.error(f"スクレイピングエラー: {e}", exc_info=True)
        return Response({
            "error": "Scraping failed",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"予期しないエラー: {e}", exc_info=True)
        return Response({
            "error": "Internal server error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def scrape_from_sitemap(request):
    """sitemap.xmlからURL一覧を取得し、各URLから企業情報をスクレイピングするエンドポイント"""
    # ファイルアップロードかURL指定かを判定
    sitemap_file = request.FILES.get('sitemap_file')
    sitemap_url = request.data.get('sitemap_url')
    value_proposition = request.data.get('value_proposition')
    
    if not sitemap_file and not sitemap_url:
        return Response({
            "error": "Validation failed",
            "message": "sitemap_file または sitemap_url のいずれかが必要です"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        logger.info(f"sitemap.xmlからの企業スクレイピングを開始: User={request.user.username}")
        
        # sitemap.xmlからURL一覧を取得
        if sitemap_file:
            # ファイルアップロードの場合
            file_content = sitemap_file.read()
            urls = parse_sitemap_from_file(file_content)
            source_url = sitemap_file.name
        else:
            # URL指定の場合
            urls = parse_sitemap_index(sitemap_url)  # sitemap indexにも対応
            source_url = sitemap_url
        
        logger.info(f"sitemap.xmlから {len(urls)} 件のURLを取得しました")
        
        if not urls:
            return Response({
                "error": "No URLs found",
                "message": "sitemap.xmlからURLが見つかりませんでした"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 複数URLからスクレイピング（最大50件まで）
        company_info = scrape_multiple_urls(urls, max_urls=50)
        
        # Companyモデルに保存
        company = Company.objects.create(
            user=request.user,
            source_url=source_url,
            scrape_source='sitemap',
            company_name=company_info.get('company_name', 'Unknown'),
            industry=company_info.get('industry'),
            business_description=company_info.get('business_description'),
            location=company_info.get('location'),
            employee_count=company_info.get('employee_count'),
            established_year=company_info.get('established_year'),
            scraped_urls=company_info.get('scraped_urls', []),
            scraped_data=company_info
        )
        
        logger.info(f"企業情報を保存しました: Company ID={company.id}")
        
        # 価値提案がある場合、分析も実行
        analysis_result = None
        if value_proposition:
            try:
                analysis_result = analyze_spin_suitability(company_info, value_proposition)
                company_analysis = CompanyAnalysis.objects.create(
                    company=company,
                    user=request.user,
                    value_proposition=value_proposition,
                    spin_suitability=analysis_result.get('spin_suitability', {}),
                    recommendations=analysis_result.get('recommendations', {})
                )
                logger.info(f"企業分析を保存しました: Analysis ID={company_analysis.id}")
            except Exception as e:
                logger.warning(f"企業分析の実行に失敗しました: {e}", exc_info=True)
        
        response_data = CompanySerializer(company).data
        response_data['urls_found'] = company_info.get('urls_found', 0)
        response_data['urls_scraped'] = company_info.get('urls_scraped', 0)
        response_data['urls_failed'] = company_info.get('urls_failed', 0)
        if analysis_result:
            response_data['analysis'] = analysis_result
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    except ValueError as e:
        logger.error(f"sitemap解析エラー: {e}", exc_info=True)
        return Response({
            "error": "Sitemap parsing failed",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"予期しないエラー: {e}", exc_info=True)
        return Response({
            "error": "Internal server error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_company(request):
    """スクレイピングした企業情報を元に、SPIN提案適合性をチェックするエンドポイント"""
    serializer = CompanyAnalyzeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        company_id = serializer.validated_data['company_id']
        value_proposition = serializer.validated_data['value_proposition']
        
        # 企業情報を取得
        company = get_object_or_404(Company, id=company_id, user=request.user)
        
        logger.info(f"企業分析を開始: Company ID={company.id}, User={request.user.username}")
        
        # 企業情報を辞書形式に変換
        company_info = {
            'company_name': company.company_name,
            'industry': company.industry,
            'business_description': company.business_description,
            'location': company.location,
            'employee_count': company.employee_count,
            'established_year': company.established_year,
            'raw_html_list': company.scraped_data.get('raw_html_list', []) if company.scraped_data else []
        }
        
        # SPIN適合性分析を実行
        analysis_result = analyze_spin_suitability(company_info, value_proposition)
        
        # CompanyAnalysisモデルに保存（既存の場合は更新）
        company_analysis, created = CompanyAnalysis.objects.update_or_create(
            company=company,
            user=request.user,
            defaults={
                'value_proposition': value_proposition,
                'spin_suitability': analysis_result.get('spin_suitability', {}),
                'recommendations': analysis_result.get('recommendations', {}),
                'analysis_details': analysis_result
            }
        )
        
        logger.info(f"企業分析を保存しました: Analysis ID={company_analysis.id}")
        
        response_data = CompanyAnalysisSerializer(company_analysis).data
        response_data['analysis'] = analysis_result
        
        return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    except ValueError as e:
        logger.error(f"企業分析エラー: {e}", exc_info=True)
        return Response({
            "error": "Analysis failed",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"予期しないエラー: {e}", exc_info=True)
        return Response({
            "error": "Internal server error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_simple_ranking(request):
    """簡易診断モードのランキングを取得するエンドポイント（認証不要）"""
    try:
        # 簡易診断モードで完了したセッションのみを対象
        finished_sessions = Session.objects.filter(
            mode='simple',
            status='finished'
        ).select_related('user', 'report').prefetch_related('messages')
        
        # レポートが存在するセッションのみを対象
        sessions_with_reports = finished_sessions.filter(report__isnull=False)
        
        # セッションごとのランキングデータを構築
        ranking_data = []
        for session in sessions_with_reports:
            report = session.report
            total_score = report.spin_scores.get('total', 0)
            message_count = session.messages.count()
            
            ranking_data.append({
                'session_id': str(session.id),
                'username': session.user.username,
                'industry': session.industry,
                'total_score': round(total_score, 1),
                'situation_score': round(report.spin_scores.get('situation', 0), 1),
                'problem_score': round(report.spin_scores.get('problem', 0), 1),
                'implication_score': round(report.spin_scores.get('implication', 0), 1),
                'need_score': round(report.spin_scores.get('need', 0), 1),
                'message_count': message_count,
                'finished_at': session.finished_at.isoformat() if session.finished_at else None,
            })
        
        # 総合スコアでソート（降順）
        ranking_data.sort(key=lambda x: x['total_score'], reverse=True)
        
        # 順位を追加
        for i, entry in enumerate(ranking_data, 1):
            entry['rank'] = i
        
        logger.info(f"簡易診断ランキング取得: {len(ranking_data)}件")
        
        return Response({
            "mode": "simple",
            "ranking": ranking_data,
            "total_sessions": len(ranking_data)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"ランキング取得エラー: {e}", exc_info=True)
        return Response({
            "error": "Failed to get ranking",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_detailed_ranking(request):
    """詳細診断モードのランキングを取得するエンドポイント（認証不要）"""
    try:
        # 詳細診断モードで完了したセッションのみを対象
        finished_sessions = Session.objects.filter(
            mode='detailed',
            status='finished'
        ).select_related('user', 'report', 'company').prefetch_related('messages')
        
        # レポートが存在するセッションのみを対象
        sessions_with_reports = finished_sessions.filter(report__isnull=False)
        
        # セッションごとのランキングデータを構築
        ranking_data = []
        for session in sessions_with_reports:
            report = session.report
            total_score = report.spin_scores.get('total', 0)
            success_probability = session.success_probability
            message_count = session.messages.count()
            
            # 総合評価スコア（スコア70% + 成功率30%）
            composite_score = (total_score * 0.7) + (success_probability * 0.3)
            
            company_name = ''
            if session.company:
                company_name = session.company.company_name or ''
            if not company_name:
                company_name = session.industry or '未設定'
            
            ranking_data.append({
                'session_id': str(session.id),
                'username': session.user.username,
                'company_name': company_name,
                'industry': session.industry or '未設定',
                'total_score': round(total_score, 1),
                'success_probability': round(success_probability, 1),
                'composite_score': round(composite_score, 1),
                'situation_score': round(report.spin_scores.get('situation', 0), 1),
                'problem_score': round(report.spin_scores.get('problem', 0), 1),
                'implication_score': round(report.spin_scores.get('implication', 0), 1),
                'need_score': round(report.spin_scores.get('need', 0), 1),
                'message_count': message_count,
                'finished_at': session.finished_at.isoformat() if session.finished_at else None,
            })
        
        # 総合評価スコアでソート（降順）
        ranking_data.sort(key=lambda x: x['composite_score'], reverse=True)
        
        # 順位を追加
        for i, entry in enumerate(ranking_data, 1):
            entry['rank'] = i
        
        logger.info(f"詳細診断ランキング取得: {len(ranking_data)}件")
        
        return Response({
            "mode": "detailed",
            "ranking": ranking_data,
            "total_sessions": len(ranking_data)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"ランキング取得エラー: {e}", exc_info=True)
        return Response({
            "error": "Failed to get ranking",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
