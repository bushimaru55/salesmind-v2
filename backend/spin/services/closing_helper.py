"""
クロージング提案を生成するヘルパー関数
商談失注（Loss Case）の判定ロジックも含む
"""
import logging
import random
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# 失注理由の定義
LOSS_REASONS = {
    'BUDGET_ISSUE': '予算不足',
    'NO_URGENCY': '導入の必要性が弱い',
    'NO_DECISION_AUTHORITY': '決裁者不在',
    'TIMING_ISSUE': '導入時期が先',
    'ALREADY_USING_COMPETITOR': '競合使用中',
    'INTERNAL_CONSTRAINT': '社内体制が整っていない',
    'FEATURE_MISMATCH': '必要な機能と合わない',
    'INFO_GATHERING_ONLY': '情報収集目的のみ',
}


def check_need_payoff_complete(session, conversation_history) -> bool:
    """
    Need-Payoff段階が完了したかどうかを判定
    
    Args:
        session: Sessionオブジェクト
        conversation_history: 会話履歴のリスト
    
    Returns:
        bool: Need-Payoffが完了している場合True
    """
    # 現在のSPIN段階がN（Need-Payoff）である
    if session.current_spin_stage != 'N':
        return False
    
    # 最近の会話でN段階のメッセージが複数回出現している
    recent_messages = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
    n_stage_count = sum(1 for msg in recent_messages 
                        if hasattr(msg, 'spin_stage') and msg.spin_stage == 'N')
    
    # N段階のメッセージが2回以上ある場合、Need-Payoffが完了したと判定
    if n_stage_count >= 2:
        return True
    
    # 成功率が一定以上（60%以上）で、かつN段階に到達している場合
    if session.success_probability >= 60 and session.current_spin_stage == 'N':
        return True
    
    return False


def generate_closing_proposal(session, conversation_history) -> Dict[str, str]:
    """
    クロージング提案を生成
    
    Args:
        session: Sessionオブジェクト
        conversation_history: 会話履歴のリスト
    
    Returns:
        Dict[str, str]: クロージング提案の種類とメッセージ
    """
    # クロージング提案のオプション
    closing_options = [
        {
            'type': '見積',
            'message': '簡易見積もりをご案内しましょうか？具体的な費用感をお伝えできます。'
        },
        {
            'type': 'デモ',
            'message': '実際のデモをご覧になりますか？具体的な使い方をご説明できます。'
        },
        {
            'type': '資料',
            'message': '導入に関する詳細資料をご案内できます。ご希望の形式でお送りします。'
        },
        {
            'type': '日程調整',
            'message': 'ご都合の良い日程を調整しましょうか？次回の打ち合わせを設定できます。'
        }
    ]
    
    # 会話の流れに応じて適切な提案を選択
    # 現在はランダムに選択（将来的には会話内容に基づいて選択可能）
    selected = random.choice(closing_options)
    
    logger.info(f"クロージング提案を生成: Session {session.id}, type={selected['type']}")
    
    return {
        'action_type': selected['type'],
        'proposal_message': selected['message']
    }


def should_trigger_closing(session, conversation_history) -> bool:
    """
    クロージングをトリガーすべきかどうかを判定
    
    【重要】SPIN不成立 → CLOSING_READY へ進まない
    
    Args:
        session: Sessionオブジェクト
        conversation_history: 会話履歴のリスト
    
    Returns:
        bool: クロージングをトリガーすべき場合True
    """
    # 既にクロージング段階に入っている場合はFalse
    if session.conversation_phase in ['CLOSING_READY', 'CLOSING_ACTION']:
        return False
    
    # 失注段階に入っている場合はFalse
    if session.conversation_phase in ['LOSS_CANDIDATE', 'LOSS_CONFIRMED']:
        return False
    
    # SPIN不成立の場合はクロージングに進まない
    # SPIN段階がN（Need-Payoff）に到達していない場合はFalse
    if session.current_spin_stage != 'N':
        return False
    
    # Need-Payoffが完了している場合
    if check_need_payoff_complete(session, conversation_history):
        return True
    
    # 会話が長すぎる場合（20回以上）でも、SPINが成立していない場合はクロージングに進まない
    # この場合は失注候補として扱う（should_trigger_closingはFalseを返す）
    
    return False


def check_loss_candidate(session, conversation_history) -> Optional[str]:
    """
    失注候補（LOSS_CANDIDATE）かどうかを判定
    
    【商談失注（Loss）条件】
    次の条件が一定回数（例：2回）連続した場合、Loss に遷移する。
    - 価値提案が業界に合致しない
    - ユーザー（営業役）が課題を理解していない
    - 営業プロセスが不自然
    - 顧客像の判断基準で合理性がない
    
    Args:
        session: Sessionオブジェクト
        conversation_history: 会話履歴のリスト
    
    Returns:
        Optional[str]: 失注理由（LOSS_REASONSのキー）またはNone
    """
    # 既に失注段階に入っている場合はNone
    if session.conversation_phase in ['LOSS_CANDIDATE', 'LOSS_CONFIRMED']:
        return None
    
    # 提案不一致が2回連続した場合
    recent_customer_messages = [
        msg for msg in conversation_history[-5:] 
        if msg.role == 'customer'
    ]
    
    # 価値提案と業界の不一致を示すキーワードをチェック
    mismatch_keywords = ['関連がない', '合わない', '違う', '関係ない', '不一致']
    mismatch_count = 0
    for msg in recent_customer_messages:
        message_lower = msg.message.lower()
        if any(keyword in message_lower for keyword in mismatch_keywords):
            mismatch_count += 1
    
    if mismatch_count >= 2:
        return 'FEATURE_MISMATCH'
    
    # SPIN不成立の場合（SPIN段階が進まない、会話が長いのにS段階のまま）
    if len(conversation_history) >= 10 and session.current_spin_stage == 'S':
        return 'NO_URGENCY'
    
    # 営業プロセスが不自然（成功率が下がり続けている）
    recent_messages_with_delta = [
        msg for msg in conversation_history[-5:]
        if hasattr(msg, 'success_delta') and msg.success_delta is not None
    ]
    if len(recent_messages_with_delta) >= 3:
        negative_count = sum(1 for msg in recent_messages_with_delta if msg.success_delta < 0)
        if negative_count >= 2:
            return 'NO_URGENCY'
    
    # 成功率が低すぎる場合（30%以下）
    if session.success_probability <= 30:
        if len(recent_customer_messages) >= 2:
            return 'NO_URGENCY'
    
    # 会話が長すぎる場合（25回以上）で、成功率が低い（40%以下）
    if len(conversation_history) >= 25 and session.success_probability <= 40:
        return 'NO_URGENCY'
    
    return None


def check_loss_confirmed(session, conversation_history, loss_reason: str) -> bool:
    """
    失注確定（LOSS_CONFIRMED）かどうかを判定
    
    Args:
        session: Sessionオブジェクト
        conversation_history: 会話履歴のリスト
        loss_reason: 失注理由
    
    Returns:
        bool: 失注確定の場合True
    """
    # 既にLOSS_CONFIRMEDの場合はTrue
    if session.conversation_phase == 'LOSS_CONFIRMED':
        return True
    
    # LOSS_CANDIDATEの状態で、追加のネガティブ反応があった場合
    if session.conversation_phase == 'LOSS_CANDIDATE':
        # 最近の顧客メッセージを確認
        recent_customer_messages = [
            msg for msg in conversation_history[-3:]
            if msg.role == 'customer'
        ]
        
        # 拒否・違和感を示すキーワードをチェック
        rejection_keywords = [
            '見送り', '予算', '時期', '検討', '必要', '決められ', '上司', '競合',
            '関連がない', '合わない', '違う', '関係ない', '不一致',
            '本日はここまで', '成立が難しい', '難しいと判断'
        ]
        
        rejection_count = 0
        for msg in recent_customer_messages:
            message_text = msg.message.lower()
            if any(keyword in message_text for keyword in rejection_keywords):
                rejection_count += 1
        
        # 拒否/違和感が2回以上続く場合は失注確定
        if rejection_count >= 2:
            return True
    
    return False


def generate_loss_response(loss_reason: str) -> Dict[str, str]:
    """
    失注確定時のAI応答テンプレートを生成
    
    Args:
        loss_reason: 失注理由（LOSS_REASONSのキー）
    
    Returns:
        Dict[str, str]: 失注確定時の応答メッセージ
    """
    loss_responses = [
        "今回は導入は見送りということで理解しました。また時期が合えばぜひご相談ください。",
        "本日はありがとうございました。またタイミングが合えばぜひご相談ください。",
        "本日のご相談は以上とさせていただきます。ご検討いただきありがとうございました。",
    ]
    
    selected_response = random.choice(loss_responses)
    
    logger.info(f"失注確定応答を生成: reason={loss_reason}")
    
    return {
        'loss_reason': loss_reason,
        'loss_reason_label': LOSS_REASONS.get(loss_reason, '不明'),
        'response_message': selected_response
    }

