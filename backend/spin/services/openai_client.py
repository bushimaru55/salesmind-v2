import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_customer_response(session, conversation_history):
    """顧客ロールプレイ用の応答を生成"""
    logger.info(f"AI顧客応答生成を開始: Session {session.id}, mode={session.mode}")
    
    # 企業情報を取得（詳細診断モードの場合）
    company_info_text = ""
    if session.mode == 'detailed' and session.company:
        company = session.company
        company_lines = []
        company_lines.append(f"企業名: {company.company_name}")
        if company.industry:
            company_lines.append(f"業界: {company.industry}")
        if company.business_description:
            company_lines.append(f"事業内容: {company.business_description}")
        if company.location:
            company_lines.append(f"所在地: {company.location}")
        if company.employee_count:
            company_lines.append(f"従業員数: {company.employee_count}")
        if company.established_year:
            company_lines.append(f"設立年: {company.established_year}")
        
        # スクレイピングデータからテキストコンテンツを取得
        if company.scraped_data:
            if company.scraped_data.get('text_content'):
                # テキストコンテンツの最初の2000文字を取得（長すぎるとエラーになるため）
                text_content = company.scraped_data.get('text_content', '')[:2000]
                company_lines.append(f"\n--- 企業のWebサイト情報 ---")
                company_lines.append(text_content)
        
        company_info_text = "\n".join(company_lines)
    
    # セッション情報から顧客人格を設定
    # 企業情報のヘッダー部分を準備（f-stringの制限を回避するため）
    company_info_section = ""
    if company_info_text:
        company_info_section = f'--- 企業情報（あなたの会社の情報） ---\n{company_info_text}\n---'
    
    # 営業担当者からの質問回数に応じて会話スタイルを段階化
    salesperson_messages = [msg for msg in conversation_history if msg.role == 'salesperson']
    question_count = len(salesperson_messages)

    if question_count == 0:
        conversation_phase_instruction = (
            "- まだ営業担当者から具体的な質問を受けていないため、丁寧に挨拶しつつ話を聞く姿勢を示し、"
            "こちらからは詳しい情報をあまり開示しないでください。回答は1〜2文で簡潔に。"
        )
    elif question_count <= 2:
        conversation_phase_instruction = (
            "- 営業担当者の質問に丁寧に答えますが、まだ慎重な姿勢を保ち、"
            "必要な範囲で情報を提供する程度にとどめてください。回答は2〜3文程度で。"
        )
    else:
        conversation_phase_instruction = (
            "- 営業担当者が複数の質問を重ね、関心が高まっている状況です。"
            "具体的な悩みや期待、導入を検討する際のポイントなどを適度に共有し、"
            "信頼関係が築けてきた様子を示してください。回答は3〜4文程度で構いません。"
        )

    system_prompt = f"""あなたは以下の企業の担当者（または社長）として、営業担当者との商談に参加しています。

業界: {session.industry}
顧客像: {session.customer_persona or '一般的な企業'}
課題・ペインポイント: {session.customer_pain or '未設定'}

{company_info_section}

重要な注意事項：
- あなたは一般的な企業の担当者や社長としてふるまってください
- 回答は必ず一人称（「私は」「当社では」など）で行い、営業担当者の質問に自然に答えてください
- あなたはSPIN法やSituation/Problem/Implication/Needといったフレームワークを認識しておらず、そのような用語を決して口にしません
- あなたは営業担当者から提案を受ける立場であり、自社サービスや製品を積極的に売り込む立場ではありません
- 営業担当者の質問に対して、企業の状況や課題、検討事項を自然な会話として返答してください
- 営業担当者から質問されていない事項については、不自然に話題を切り出さず、会話の流れに沿って答えてください
- 初期の挨拶では丁寧に感謝を述べつつも、提案内容を理解したいというニュートラルな姿勢を示してください
- 営業担当者から説明を受けるまでは、自社製品やサービスを自ら売り込むような発言は控えてください
{conversation_phase_instruction}"""
    
    # 企業情報がある場合は追加の指示を追加
    if company_info_text:
        system_prompt += "\n- 上記の企業情報（会社名、事業内容、所在地など）を参考にして、具体的で現実味のある応答をしてください"
    else:
        system_prompt += "\n- 企業情報が限られている場合でも、業界や営業担当者から提供された情報をもとに現実的な内容で回答してください"
    
    system_prompt += """
- 質問に対しては事実を答えますが、すべてを一度に明かす必要はありません（抵抗を示したり、慎重になる場合もあります）
- 営業が質問してくることに対して、逆に質問したり、SPIN法のような構造化された質問をすることはありません
- 単純に、営業からの質問に対する回答や、状況の説明を行うだけです
- 企業の実務者として、課題や悩みを自然に共有しますが、それは営業手法を意識したものではありません
- 回答はすべて自然な日本語で、2〜4文程度のまとまりで返答してください
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
        logger.info(f"AI顧客応答生成が完了: Session {session.id}, mode={session.mode}, 応答長: {len(response_content)}文字")
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

