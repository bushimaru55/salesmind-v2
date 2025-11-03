import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_customer_response(session, conversation_history):
    """顧客ロールプレイ用の応答を生成"""
    logger.info(f"AI顧客応答生成を開始: Session {session.id}")
    # セッション情報から顧客人格を設定
    system_prompt = f"""あなたは以下の顧客を演じるAIです。営業担当者との商談で自然な会話を行ってください。

業界: {session.industry}
顧客像: {session.customer_persona or '一般的な企業'}
課題・ペインポイント: {session.customer_pain or '未設定'}

あなたの役割：
- 営業担当者の質問に対して、設定された顧客像に基づいて自然に応答する
- SPIN質問に対して適切な深さで応答する（すぐに答えすぎない、抵抗を示す場合もある）
- 会話の流れに沿って自然な反応を生成する
- 営業担当者が深掘りする余地を残しながら、必要な情報は提供する
"""
    
    # 会話履歴をメッセージ形式に変換
    messages = [{"role": "system", "content": system_prompt}]
    
    for msg in conversation_history:
        if msg.role == 'salesperson':
            messages.append({"role": "user", "content": msg.message})
        elif msg.role == 'customer':
            messages.append({"role": "assistant", "content": msg.message})
    
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.8,
        )
        response_content = res.choices[0].message.content
        logger.info(f"AI顧客応答生成が完了: Session {session.id}, 応答長: {len(response_content)}文字")
        return response_content
    except Exception as e:
        logger.error(f"AI顧客応答生成エラー: Session {session.id}, Error: {str(e)}", exc_info=True)
        raise


def generate_spin(industry, value_prop, persona=None, pain=None):
    """SPIN質問を生成する"""
    logger.info(f"SPIN質問生成を開始: Industry={industry}, ValueProp={value_prop[:50]}...")
    prompt = f"""
あなたはB2B営業コーチです。以下の情報を基に、SPIN思考に基づいた営業質問を生成してください。

業界: {industry}
価値提案: {value_prop}
"""
    if persona:
        prompt += f"顧客像: {persona}\n"
    if pain:
        prompt += f"顧客の課題: {pain}\n"
    
    prompt += """
SPIN各要素（Situation, Problem, Implication, Need）ごとに、実際の商談で使用できる質問を3〜5個ずつ日本語で生成してください。
各質問は自然で、顧客の状況を深掘りできるものにしてください。

以下のJSON形式で返してください：
{
  "situation": ["質問1", "質問2", "質問3"],
  "problem": ["質問1", "質問2", "質問3"],
  "implication": ["質問1", "質問2", "質問3"],
  "need": ["質問1", "質問2", "質問3"]
}
"""
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは営業コーチAIです。必ずJSON形式で回答してください。"},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        response_content = res.choices[0].message.content
        logger.info(f"SPIN質問生成が完了: Industry={industry}")
        return response_content
    except Exception as e:
        logger.error(f"SPIN質問生成エラー: Industry={industry}, Error: {str(e)}", exc_info=True)
        raise

