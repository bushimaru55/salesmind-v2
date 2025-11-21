"""
顧客温度スコア（0〜100）を計算するモジュール

科学的裏付けに基づく顧客の反応を定量化し、
興味・関心・不安・購買意欲の上下をリアルタイムで可視化する。
"""
import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)

# 購買シグナルのキーワードとスコア
# 営業学のBuying Signal理論に基づく
BUYING_SIGNAL_POSITIVE = {
    # 具体的な質問（+10点）
    '具体的には': 10,
    '費用は': 10,
    '料金は': 10,
    '価格は': 10,
    'いくら': 10,
    '詳細': 10,
    '詳しく': 10,
    # 成約意欲直接指標（+20点）
    '導入': 20,
    '契約': 20,
    '日程': 20,
    'いつ': 20,
    '開始': 20,
    '検討': 15,
    '決め': 15,
    '進め': 15,
}

# 顧客の前向き反応キーワード（温度スコアに追加加点）
CUSTOMER_POSITIVE_RESPONSES = {
    # 興味・関心（+10点）
    '興味があります': 10,
    '興味がある': 10,
    '関心': 10,
    '詳しく聞きたい': 10,
    '詳しく教えて': 10,
    # デモ・体験希望（+15点）
    'デモを見たい': 15,
    'デモを見': 15,
    'デモを': 15,
    '無料体験したい': 15,
    '無料体験': 15,
    '体験': 15,
    'トライアル': 15,
    # 導入意欲（+15点）
    '導入に前向き': 15,
    '導入を検討': 15,
    '導入したい': 15,
    '導入を考え': 15,
    # 価値認識（+10点）
    '価値を感じる': 10,
    '価値がある': 10,
    'メリット': 10,
    '効果': 10,
    # 検討意欲（+10点）
    '検討したい': 10,
    '検討します': 10,
    '検討させて': 10,
    # 具体的な質問（+5点）
    'どのように': 5,
    'どういう': 5,
    'どんな': 5,
}

# 社内承認・予算理由（ペナルティなし）
INTERNAL_APPROVAL_REASONS = [
    '社内で検討',
    '社内の承認',
    '社内で相談',
    '上司に確認',
    '役員に相談',
    '予算の確保',
    '予算を確保',
    '予算を検討',
    '予算を確認',
    '予算が',
    '決裁',
    '承認',
]

BUYING_SIGNAL_NEGATIVE = {
    # 反対理由指標（-10〜-20点）
    '高い': -15,
    '無理': -20,
    '難しい': -15,
    'できない': -15,
    '不要': -20,
    'いらない': -20,
    '興味ない': -20,
    '違う': -10,
    '合わない': -15,
}

# 認知負荷のキーワード
# 心理学の認知負荷理論に基づく
COGNITIVE_LOAD_NEGATIVE = {
    'わかりません': -15,
    '難しい': -15,
    '理解できない': -15,
    '複雑': -10,
    '混乱': -10,
}

COGNITIVE_LOAD_POSITIVE = {
    '理解できました': 10,
    '助かります': 10,
    'わかりました': 8,
    '納得': 8,
    'なるほど': 5,
}


def calculate_sentiment_score(sentiment: float) -> float:
    """
    感情スコアを計算（0〜50点）
    
    Args:
        sentiment: LLMから取得した感情スコア（-1.0〜+1.0）
    
    Returns:
        float: 0〜50点の感情スコア
    
    根拠: 感情分析はNLPの標準技法
    """
    # 変換式: sentiment_score = (sentiment + 1) * 25
    sentiment_score = (sentiment + 1) * 25
    return max(0, min(50, sentiment_score))


def calculate_buying_signal_score(message: str) -> float:
    """
    購買シグナルスコアを計算（-20〜+20点）
    
    【改善】顧客の前向き反応を重視し、社内承認・予算理由はペナルティなし
    
    Args:
        message: 顧客のメッセージ
    
    Returns:
        float: -20〜+20点の購買シグナルスコア
    
    根拠: 購買シグナルは営業学のBuying Signal理論
    """
    message_lower = message.lower()
    score = 0
    
    # 社内承認・予算理由をチェック（ペナルティなし）
    has_internal_reason = any(reason in message_lower for reason in INTERNAL_APPROVAL_REASONS)
    
    # ポジティブシグナルをチェック
    for keyword, points in BUYING_SIGNAL_POSITIVE.items():
        if keyword in message_lower:
            score += points
    
    # ネガティブシグナルをチェック（社内承認・予算理由の場合はペナルティなし）
    if not has_internal_reason:
        for keyword, points in BUYING_SIGNAL_NEGATIVE.items():
            if keyword in message_lower:
                score += points
    
    return max(-20, min(20, score))


def calculate_customer_positive_response_score(message: str) -> float:
    """
    顧客の前向き反応スコアを計算（0〜+30点）
    
    【新規追加】顧客の前向き反応（興味・質問・デモ希望等）を重視
    
    Args:
        message: 顧客のメッセージ
    
    Returns:
        float: 0〜+30点の前向き反応スコア
    """
    message_lower = message.lower()
    score = 0
    
    # 前向き反応キーワードをチェック
    for keyword, points in CUSTOMER_POSITIVE_RESPONSES.items():
        if keyword in message_lower:
            score += points
    
    # 最大30点に制限
    return min(30, score)


def calculate_cognitive_load_score(message: str) -> float:
    """
    認知負荷スコアを計算（-15〜+10点）
    
    Args:
        message: 顧客のメッセージ
    
    Returns:
        float: -15〜+10点の認知負荷スコア
    
    根拠: 認知負荷は心理学（認知負荷理論）
    """
    message_lower = message.lower()
    score = 0
    
    # ネガティブな認知負荷をチェック
    for keyword, points in COGNITIVE_LOAD_NEGATIVE.items():
        if keyword in message_lower:
            score += points
    
    # ポジティブな認知負荷をチェック
    for keyword, points in COGNITIVE_LOAD_POSITIVE.items():
        if keyword in message_lower:
            score += points
    
    return max(-15, min(10, score))


def calculate_engagement_score(message: str) -> float:
    """
    エンゲージメントスコアを計算（-5〜+10点）
    
    Args:
        message: 顧客のメッセージ
    
    Returns:
        float: -5〜+10点のエンゲージメントスコア
    
    根拠: 文章量は顧客エンゲージメント指標として一般的に使用される
    """
    message_length = len(message)
    
    if message_length < 10:
        return -5
    elif message_length < 30:
        return 0
    elif message_length < 80:
        return 5
    else:
        return 10


def calculate_question_score(message: str) -> float:
    """
    質問頻度スコアを計算（0〜15点）
    
    Args:
        message: 顧客のメッセージ
    
    Returns:
        float: 0〜15点の質問頻度スコア
    
    根拠: 質問数は顧客エンゲージメント指標として一般的に使用される
    """
    question_count = message.count("？") + message.count("?")
    question_score = min(question_count * 5, 15)
    return question_score


def analyze_sentiment_with_llm(message: str) -> float:
    """
    LLMを使用して感情スコアを分析（-1.0〜+1.0）
    
    Args:
        message: 顧客のメッセージ
    
    Returns:
        float: -1.0〜+1.0の感情スコア
    """
    try:
        import os
        from openai import OpenAI
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""以下の顧客の発言を分析し、感情スコアを-1.0〜+1.0の範囲で返してください。
-1.0: 非常にネガティブ、不満、拒否
0.0: ニュートラル
+1.0: 非常にポジティブ、興味、前向き

顧客の発言: {message}

JSON形式で返してください:
{{"sentiment": 0.0}}
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは感情分析の専門家です。必ずJSON形式で返答してください。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        sentiment = float(result.get("sentiment", 0.0))
        
        # -1.0〜+1.0の範囲にクリップ
        sentiment = max(-1.0, min(1.0, sentiment))
        
        return sentiment
    except Exception as e:
        logger.warning(f"感情分析に失敗しました: {e}", exc_info=True)
        # エラー時はニュートラル（0.0）を返す
        return 0.0


def calculate_temperature_score(message: str, use_llm: bool = True, spin_penalty: float = 0.0, closing_style: str = None) -> Dict[str, float]:
    """
    顧客温度スコア（0〜100）を計算
    
    【改善】SPIN順序ペナルティの緩和、前向き反応の重視、現実仕様への補正
    
    Args:
        message: 顧客のメッセージ
        use_llm: LLMを使用して感情分析を行うか（デフォルト: True）
        spin_penalty: SPIN順序違反によるペナルティ（デフォルト: 0.0）
        closing_style: クロージングスタイル（"option_based" / "one_shot_push" / None）
    
    Returns:
        Dict[str, float]: 温度スコアの詳細情報
        {
            "sentiment": 0.0,  # LLMから取得した感情スコア（-1.0〜+1.0）
            "sentiment_score": 25.0,  # 変換後の感情スコア（0〜50）
            "buying_signal": 10.0,  # 購買シグナルスコア（-20〜+20）
            "cognitive_load": -5.0,  # 認知負荷スコア（-15〜+10）
            "engagement": 5.0,  # エンゲージメントスコア（-5〜+10）
            "question_score": 10.0,  # 質問頻度スコア（0〜15）
            "positive_response": 10.0,  # 前向き反応スコア（0〜30）【新規追加】
            "spin_penalty": -2.0,  # SPIN順序ペナルティ（緩和後）【新規追加】
            "closing_bonus": 0.0,  # クロージングスタイルボーナス【新規追加】
            "temperature": 75.0  # 総合温度スコア（0〜100、現実仕様に補正）
        }
    """
    # ① 感情スコア（Sentiment）
    if use_llm:
        sentiment = analyze_sentiment_with_llm(message)
    else:
        # LLMを使用しない場合は簡易的な感情分析
        sentiment = 0.0  # デフォルトはニュートラル
    
    sentiment_score = calculate_sentiment_score(sentiment)
    
    # ② 購買シグナルスコア（Buying Signal）
    buying_signal_score = calculate_buying_signal_score(message)
    
    # ③ 認知負荷スコア（Cognitive Load）
    cognitive_score = calculate_cognitive_load_score(message)
    
    # ④ エンゲージメントスコア（文章量）
    engagement_score = calculate_engagement_score(message)
    
    # ⑤ 質問頻度スコア（Interest Level）
    question_score = calculate_question_score(message)
    
    # ⑥ 顧客の前向き反応スコア（新規追加）
    positive_response_score = calculate_customer_positive_response_score(message)
    
    # ⑦ SPIN順序ペナルティの緩和
    # 順序違反ペナルティを最大30%に制限
    adjusted_spin_penalty = spin_penalty * 0.3
    
    # 顧客の前向き反応が1つでもあれば、順序ペナルティをさらに軽減（50%）
    if positive_response_score > 0:
        adjusted_spin_penalty = adjusted_spin_penalty * 0.5
    
    # ⑧ クロージングスタイルの評価
    closing_bonus = 0.0
    if closing_style == "option_based":
        # 選択肢型クロージング（例：「デモと無料体験、どちらで進めましょう？」）
        closing_bonus = 10.0
    elif closing_style == "one_shot_push":
        # 一気に押すクロージング（軽度の減点のみ）
        closing_bonus = -5.0
    
    # 総合スコア算出式（0〜100）
    total = (
        sentiment_score
        + buying_signal_score
        + cognitive_score
        + engagement_score
        + question_score
        + positive_response_score  # 前向き反応スコアを追加
        + adjusted_spin_penalty  # SPIN順序ペナルティ（緩和後）を追加
        + closing_bonus  # クロージングスタイルボーナスを追加
    )
    
    # 負の値が大きすぎる場合は0にクリップ（補正前に）
    total = max(0, total)
    
    # 顧客温度を40〜70の中間値で揺らがせる調整
    # 20〜40：慎重（冷たくない）
    # 40〜60：普通（最適値）
    # 60〜80：前向き（課題に合致すれば温度上昇）
    
    # 現実仕様への補正（スコア補正係数1.25を適用）
    # ただし、元のスコアが低い場合は補正を控えめにする
    if total > 0:
        # 補正係数を段階的に適用（低スコアの場合は補正を控えめに）
        if total < 20:
            correction_factor = 1.1  # 低スコアの場合は控えめに補正
        elif total < 40:
            correction_factor = 1.15
        else:
            correction_factor = 1.25  # 高スコアの場合は通常の補正
        total = total * correction_factor
        
        # 温度を40〜70の中間値に調整（最低40、最高80）
        if total < 40:
            # 低いスコアでも最低40程度にする（冷たくない）
            total = 40 + (total * 0.1)  # 40〜44程度に調整
        elif total > 80:
            # 高いスコアは80程度に上限を設ける
            total = min(80, total)
    else:
        # スコアが0の場合は最低40に設定（冷たくない）
        total = 40
    
    # 正規化して0〜100に収める
    temperature = max(0, min(100, total))
    
    return {
        "sentiment": sentiment,
        "sentiment_score": round(sentiment_score, 1),
        "buying_signal": round(buying_signal_score, 1),
        "cognitive_load": round(cognitive_score, 1),
        "engagement": round(engagement_score, 1),
        "question_score": round(question_score, 1),
        "positive_response": round(positive_response_score, 1),
        "spin_penalty": round(adjusted_spin_penalty, 1),
        "closing_bonus": round(closing_bonus, 1),
        "temperature": round(temperature, 1),
    }

