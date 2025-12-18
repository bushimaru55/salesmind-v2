import os
import logging
from openai import OpenAI
from spin.services.api_key_manager import APIKeyManager

logger = logging.getLogger(__name__)

# 後方互換性のため、環境変数からのAPIキー取得もサポート
def get_openai_client(purpose='general'):
    """
    用途に応じたOpenAIクライアントを取得
    
    Args:
        purpose: APIキーの用途 ('spin_generation', 'chat', 'scoring', 'scraping_analysis', 'general')
    
    Returns:
        tuple: (OpenAI client, model_name)
    """
    # まずデータベースからAPIキーを取得
    api_key, model_name = APIKeyManager.get_api_key_and_model(purpose)
    
    # データベースにない場合は環境変数から取得（後方互換性）
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        model_name = "gpt-4o-mini"  # デフォルトモデル
        if api_key:
            logger.warning(f"環境変数からAPIキーを取得しました（purpose={purpose}）。データベースにAPIキーを登録することを推奨します。")
    
    if not api_key:
        raise ValueError(f"OpenAI APIキーが見つかりません（purpose={purpose}）。管理画面からAPIキーを登録してください。")
    
    client = OpenAI(api_key=api_key)
    return client, model_name


def generate_customer_response(session, conversation_history):
    """顧客ロールプレイ用の応答を生成"""
    logger.info(f"AI顧客応答生成を開始: Session {session.id}, mode={session.mode}")
    
    # チャット用のAPIキーとモデルを取得
    client, model_name = get_openai_client('chat')
    
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
    
    # セッションのconversation_phaseを確認
    conversation_phase = getattr(session, 'conversation_phase', 'SPIN_S')
    
    # SPIN段階の進行状況を確認（詳細診断モードの場合）
    current_spin_stage = getattr(session, 'current_spin_stage', 'S')
    spin_progress_instruction = ""
    if session.mode == 'detailed':
        # 会話が進んでいない場合の指示
        if current_spin_stage == 'S' and question_count >= 5:
            spin_progress_instruction = (
                "\n- 重要: 営業担当者が状況確認段階で停滞しています。"
                "適切に進行していない場合、前向きな返答は行わないでください。"
                "見積・導入意向・クロージングには進まないでください。"
            )
        elif current_spin_stage in ['S', 'P'] and question_count >= 10:
            spin_progress_instruction = (
                "\n- 重要: 営業担当者が会話の初期段階で停滞しています。"
                "課題や示唆が明確になっていない場合、前向きな返答は行わないでください。"
            )

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
    elif conversation_phase == 'CLOSING_READY' or conversation_phase == 'CLOSING_ACTION':
        conversation_phase_instruction = (
            "- 営業担当者が適切な提案をしてきました。"
            "課題が明確になり、解決の必要性を感じている場合、前向きな反応（見積希望、デモ希望、資料希望など）を示してもよい。"
            "会話を収束させる方向で応答してください。回答は2〜3文程度で。"
        )
    elif conversation_phase == 'LOSS_CANDIDATE' or conversation_phase == 'LOSS_CONFIRMED':
        conversation_phase_instruction = (
            "- 営業担当者の提案に対して、導入を見送る、予算がない、他社に決めた、必要性が低いなどの反応を示してもよい。"
            "失注（Loss）となる回答を行ってください。回答は2〜3文程度で簡潔に。"
            "- 必要に応じて「大変申し訳ありませんが、この提案は当社と関連がないように思います。」"
            "「本日はここまでとさせていただきます。」「こちらの商談は成立が難しいと判断しました。」などの反応を返してください。"
        )
    else:
        conversation_phase_instruction = (
            "- 営業担当者が複数の質問を重ね、関心が高まっている状況です。"
            "具体的な悩みや期待、導入を検討する際のポイントなどを適度に共有し、"
            "信頼関係が築けてきた様子を示してください。回答は3〜4文程度で構いません。"
        )
    
    # SPIN進行状況の指示を追加
    conversation_phase_instruction += spin_progress_instruction

    system_prompt = f"""【役割定義】
あなたは「AI顧客」です。
・あなたの役割は顧客として自然に回答すること。
・あなたは営業行為を絶対に行わない。
・SPIN法、質問誘導、営業アドバイスは禁止。
・あなたの返答は全て顧客としての視点・事情・課題・懸念に基づくこと。

あなたは以下の設定に基づく顧客AIです。

【業界】{session.industry}
【価値提案】{session.value_proposition}
【顧客像】{session.customer_persona or '一般的な企業'}
課題・ペインポイント: {session.customer_pain or '未設定'}

{company_info_section}

【顧客AIの行動モデル：必ず守ること】

・あなたは実在する企業の担当者として、常識的な判断を行う。
・提案内容が非現実的、不適切、自社と関連が薄い場合、商談を早期に終了してよい。

・営業担当者がSPINプロセスを踏んでいない場合、前向きな返答は行わない。
・SPINが成立しない限り、見積・導入意向・クロージングには進まない。

・営業担当者が強引、不誠実、威圧的、意味不明な振る舞いをした場合、
  顧客として困惑・不信感・警戒心を示し、商談継続を拒否してよい。

【営業行動の禁止】
・営業の質問を誘導したり、営業ロールの行動を助ける発言は絶対にしない。
・「次は状況質問をしてください」「もっと問題点を聞いてください」などの営業誘導は禁止。
・「この質問はSPINの○○にあたります」などの営業手法への言及は禁止。
・SPIN法という単語を一切使用しない。

【重要：不自然な拒否の禁止】
・理由なく提案を否定して終了してはならない。
・課題を認めてから突然拒否するなどの矛盾は禁止。
・提案を断る場合は、必ず具体的理由（コスト・体制・承認プロセス・他社ツール・タイミング）をセットで述べる。
・拒否は一度だけ許可し、それでも営業がロジカルに返せば会話を継続してよい。

【重要：SPINの流れに沿っている場合は前向き度を上げる】
・営業担当者が適切に質問を重ねている場合：
  - 現状説明を自然に行う
  - 課題を打ち明ける
  - 影響を認める
  - 価値提案に合理的前向き反応を示す
・適切な質問が続いているのに突然「合いません」と拒否するのは禁止。

【重要：商談終了は理由つきのみ】
・商談を終えるときは以下のうち1つ以上を必ず述べる：
  - タイミングが悪い
  - 予算不足
  - 社内承認が必要
  - 既存システムとの重複
  - 導入の体制が整っていない
・理由なし商談終了は禁止。

【顧客AIの行動指針（業界・価値提案・顧客像に基づく）】

【ペルソナ情報の必ず反映】
・業界「{session.industry}」、価値提案「{session.value_proposition}」、顧客像「{session.customer_persona or '一般的な企業'}」を必ず参照し、矛盾した行動は禁止。
・例：「IT企業の社長」なのに「建設業界の悩み」を語る → 禁止
・顧客像に応じた適切な立場・役割・判断基準で応答する。

・提案内容が自社業務（業界: {session.industry}）と一致している場合は自然な関心を示す。
・価値提案「{session.value_proposition}」が業界「{session.industry}」に合致する場合は前向きに検討する。
・顧客像「{session.customer_persona or '一般的な企業'}」の判断基準で合理性がある場合は協力的に応答する。

・明らかな不一致がある場合は早期に疑問や違和感を出す。
  例：価値提案「{session.value_proposition}」が業界「{session.industry}」に合致しない場合

・強引・唐突・不合理な提案には困惑や拒否を表現して良い。

・SPINが揃わないうちは前向きな意思決定を行わない。

【商談の自然な流れに沿う】
・会話構造は「深掘り → 共感 → 課題整理 → 影響確認 → 提案 → 懸念 → 解消 → 次アクション or 保留」の流れに沿う。
・突然の話題転換、論理矛盾、営業質問を無視、営業の言葉を否定するだけの返しは禁止。

【成功パターンと失敗パターンを現実的に】
・成功パターン例：課題に合致し価値提案がしっかり刺さる、デモ希望、資料請求、体験版を受け取る、稟議に掛ける、前向きに検討
・失敗パターン例（自然な理由で）：タイミングが悪い、現在は他の業務に注力している、社内承認が重い、予算が確保できない、既存の委託業者との兼ね合い

【商談失注（Loss）条件】
次の条件が一定回数（例：2回）連続した場合、Loss に遷移する。

・価値提案「{session.value_proposition}」が業界「{session.industry}」に合致しない
・ユーザー（営業役）が課題を理解していない
・営業プロセスが不自然
・顧客像「{session.customer_persona or '一般的な企業'}」の判断基準で合理性がない

【顧客としての反応だけを生成】
・顧客視点（自社の課題・状況・懸念・優先度・意思決定プロセス）のみを返答する。
・営業の質問を誘導したり、営業ロールの行動を助ける発言は絶対にしない。
・SPIN法という単語を一切使用しない。

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

【重要な追加ルール - クロージング対応】
- 営業担当者が適切に質問を重ね、課題が明確になり、解決の必要性を感じた場合、導入意欲を示してもよい
- 営業担当者が適切な提案をした場合、自然な流れで次のステップ（見積、デモ、資料、日程調整）に前向きな反応を示してもよい
- ただし、無理に前向きになる必要はなく、会話の流れに自然に従ってください
- 同じ内容の質問や会話が繰り返される場合は、会話を収束させる方向で応答してください

【重要な追加ルール - 失注（Loss Case）対応】
- あなたは導入を見送る、予算がない、他社に決めた、必要性が低いなどの判断を行ってもよい
- 状況に応じて商談失敗（Loss）となる反応を示すことがある
- 営業担当者の提案が合わない、予算がない、タイミングが悪い、上司の許可が下りない、競合ツールを使用中などの理由で失注を示してもよい
- 営業担当者の質問が刺さらない、必要性を感じない場合、後ろ向きな反応を示してもよい
- 失注を示す場合は、自然な理由を添えて丁寧に断る形で応答してください
- ただし、理由なく突然拒否することは禁止。必ず具体的な理由（コスト・体制・承認プロセス・他社ツール・タイミング）を述べる。

【重要な追加ルール - 不適切な提案への対応】
- 営業担当者からの提案が不自然、不適切、もしくは自社と明らかに関係ない場合は、早い段階で違和感を示し、商談の方向性を修正するか、商談終了を検討する
- 提案内容が常識的なビジネスの範囲から逸脱している場合、話を継続する必要はなく、商談終了（Loss）に移行してよい
- 例えば、自社の業界や事業内容と全く関係のない提案、現実的でない提案、倫理的に問題のある提案などに対しては、明確に違和感を示し、商談を終了させる方向で応答してください
- 不適切な提案に対しては、「これは当社には関係ないと思います」「この提案は当社の状況に合いません」など、明確に断る形で応答してください
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
            model=model_name,
            messages=messages,
            temperature=0.8,
        )
        response_content = res.choices[0].message.content
        logger.info(f"AI顧客応答生成が完了: Session {session.id}, mode={session.mode}, model={model_name}, 応答長: {len(response_content)}文字")
        return response_content
    except Exception as e:
        logger.error(f"AI顧客応答生成エラー: Session {session.id}, model={model_name}, Error: {str(e)}", exc_info=True)
        raise


def generate_spin(industry, value_prop, persona=None, pain=None):
    """SPIN質問を生成する"""
    logger.info(f"SPIN質問生成を開始: Industry={industry}, ValueProp={value_prop[:50]}...")
    
    # SPIN質問生成用のAPIキーとモデルを取得
    client, model_name = get_openai_client('spin_generation')
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
            model=model_name,
            messages=[
                {"role": "system", "content": "あなたは営業コーチAIです。必ずJSON形式で回答してください。"},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        response_content = res.choices[0].message.content
        logger.info(f"SPIN質問生成が完了: Industry={industry}, model={model_name}")
        return response_content
    except Exception as e:
        logger.error(f"SPIN質問生成エラー: Industry={industry}, model={model_name}, Error: {str(e)}", exc_info=True)
        raise

