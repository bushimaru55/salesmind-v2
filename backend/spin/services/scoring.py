"""
スコアリング用プロンプトテンプレート
"""
import os
import logging
from typing import Tuple
from spin.services.ai_provider_factory import AIProviderFactory
from spin.models import AIModel

logger = logging.getLogger(__name__)

def get_client_and_model_for_scoring() -> Tuple:
    """スコアリング用のクライアントとモデルを取得（新しいシステム）"""
    client, model = AIProviderFactory.get_client_and_model_for_purpose('scoring')
    if not client or not model:
        raise ValueError("スコアリング用のAPIキーとモデルが見つかりません。管理画面から設定してください。")
    return client, model


def score_conversation(session, conversation_history):
    """会話履歴を分析してスコアリングを実行"""
    logger.info(f"スコアリング開始: Session {session.id}, mode={session.mode}, メッセージ数: {len(conversation_history)}")
    
    # スコアリング用のAPIキーとモデルを取得
    client, model = get_client_and_model_for_scoring()
    model_name = model.model_id
    logger.info(f"スコアリング使用モデル: {model.provider} / {model_name}")
    # 会話履歴をテキスト形式に変換
    conversation_text = ""
    irrelevant_topics = []  # 営業とは関係ない話題を記録
    
    # 営業とは関係ない話題のキーワード
    irrelevant_keywords = [
        'トイレ', 'お手洗い', '便所', '化粧室',
        '天気', '雨', '晴れ', '気温',
        'ランチ', '昼食', '食事', 'ご飯',
        '趣味', 'スポーツ', '映画', '音楽',
        'プライベート', '家族', '友人',
        '今日の', '昨日の', '明日の',
    ]
    
    for msg in conversation_history:
        role_name = "営業担当者" if msg.role == 'salesperson' else "顧客"
        message_text = msg.message.lower()
        
        # 営業担当者の発言で、営業とは関係ない話題を検出
        if msg.role == 'salesperson':
            for keyword in irrelevant_keywords:
                if keyword in message_text:
                    # 業界・価値提案・顧客の課題と関連性があるかチェック
                    is_irrelevant = True
                    if session.industry and session.industry.lower() in message_text:
                        is_irrelevant = False
                    if session.value_proposition and session.value_proposition.lower() in message_text:
                        is_irrelevant = False
                    if session.customer_pain and session.customer_pain.lower() in message_text:
                        is_irrelevant = False
                    
                    if is_irrelevant:
                        irrelevant_topics.append(f"「{msg.message}」")
                        break
        
        conversation_text += f"{role_name}: {msg.message}\n"
    
    # 営業とは関係ない話題の警告文を準備
    irrelevant_warning = ""
    if irrelevant_topics:
        irrelevant_warning = f"""
【重要：営業とは関係ない話題の検出】
以下の営業担当者の発言は、営業商談とは明らかに関係ない話題です：
{chr(10).join(irrelevant_topics)}

これらの発言は営業スキルとして評価すべきではありません。大幅な減点を適用してください。
"""
    
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
        company_info_text = "\n".join(company_lines)
    
    # 企業情報セクションを準備（f-stringの制限を回避するため）
    company_info_section = ""
    company_info_note = ""
    if company_info_text:
        # f-string内でバックスラッシュを使わないようにする
        newline = "\n"
        company_info_section = f'--- 企業情報（実際の顧客企業の情報） ---{newline}{company_info_text}{newline}---'
        company_info_note = '上記の企業情報を参考に、営業担当者が実際の企業情報に基づいた適切な質問をしているかを評価してください。'
    
    prompt = f"""【役割定義】
あなたは「スコアリングAI」です。
・営業の論理性・深掘り・価値提案の一貫性のみ評価する。
・顧客の事情による失注は減点対象としない。
・営業の発言内容・深掘り度・価値訴求を評価する。
・顧客が「予算がない」「忙しい」などの理由で断っても、営業側の行動が正しければ高スコアを出す。
・「失注＝低評価」にはしない。

あなたは営業スキル評価の専門家です。以下の会話履歴を分析し、5つの要素で総合スコアを構成してスコアリングを行ってください。

セッション情報:
- 業界: {session.industry}
- 価値提案: {session.value_proposition}
- 顧客像: {session.customer_persona or '未設定'}
注意: 顧客の課題は事前に設定されていません。営業担当者が会話を通じて顧客の課題を聞き出すことが重要です。

{company_info_section}
注意: {company_info_note}

会話履歴:
{conversation_text}

{irrelevant_warning}

【重要】評価の対象は「営業担当者の発言・行動・質問の質」です。
顧客の事情（予算不足、タイミング、社内承認など）による失注は、営業の評価に影響させないでください。

【重要】5つの要素で総合スコア（100点満点）を構成してください。

●① 探索力（Situation/Problem 深掘り）…20点
  - 業界・企業の基本情報を確認できているか
  - 現在のシステム・体制を把握できているか
  - 顧客の課題を聞き出せているか
  - 課題の具体的な内容を把握できているか
  - 問題の根本原因を探れているか

●② 影響の引き出し（Implication）…20点
  - 問題の影響範囲を把握できているか
  - 問題を放置した場合のリスクを明確にできているか
  - 緊急性を理解できているか
  - 顧客の感情面への影響を考慮できているか

●③ 価値提案の的確さ（Need-payoff）…20点
  - 顧客の理想的な解決策のイメージを把握できているか
  - 価値提案が顧客の課題に合致しているか
  - 顧客の予算・リソース制約を理解できているか
  - 顧客の意思決定プロセスを把握できているか

●④ 顧客の反応と整合性 …20点
  - 営業の質問と顧客の回答が噛み合っているか
  - 顧客の反応に適切に対応できているか
  - 論理矛盾がないか
  - 会話全体の一貫性があるか

●⑤ 商談前進度（デモ・体験・資料など）…20点
  - 具体的な次のステップへの合意形成ができているか
  - デモ・体験・資料請求などの前進があるか
  - 商談が自然に前進しているか

【スコアリングの重要原則】
1. SPIN順守は評価項目ではなく"加点要素"に変更する。順番がズレても内容が良ければ高得点維持。
2. 商談が不成立でも、課題深掘りができている・顧客への共感が適切・論理に破綻がない場合は 60〜75点 になるように調整。
3. 強引・質問をしない・価値提案が不一致の場合は 20〜40点。
4. 成功（資料請求・体験申込）時は 80〜95点。
5. 自然な流れなのに低スコア、顧客の温度に左右されすぎる、顧客が拒否しても営業に非がないのに低評価は禁止。
6. 【最重要】営業の責任と顧客事情を完全に分離して採点する。顧客が「予算がない」「タイミングが悪い」「社内承認が必要」などの理由で断っても、営業側の行動が正しければ高スコアを出す。
7. 論理矛盾なし・問いと答えが噛み合っている・課題が自然に深掘りされている、この3つが揃えば最低 60点以上とする。
8. 顧客の事情による失注（予算不足、タイミング、社内承認など）は、営業の評価に影響させない。
9. 【最重要】営業とは明らかに関係ない話をした場合は、大幅な減点を適用してください。
   - 営業とは関係ない話の例：
     * 「トイレを貸してください」「お手洗いはどこですか」などの物理的な要求
     * 「天気の話」「趣味の話」「プライベートな話」など、営業商談と無関係な話題
     * 「今日のランチは何を食べましたか？」などの雑談
     * 業界・価値提案・顧客の課題と全く関係ない話題
   - 減点基準：
     * 営業とは明らかに関係ない話が1回でも含まれている場合：総合スコアから20〜30点を減点
     * 営業とは関係ない話が複数回含まれている場合：総合スコアから30〜50点を減点
     * 営業とは関係ない話が会話の大部分を占めている場合：総合スコアを0〜20点に制限
   - 営業とは関係ない話をした場合でも、他の要素（探索力、影響の引き出しなど）は通常通り評価してください。
     ただし、総合スコアには上記の減点を適用してください。

評価結果をJSON形式で返してください。必ずJSON形式で返してください。
{{
  "exploration": <0-20の整数>,  // 探索力（Situation/Problem 深掘り）
  "implication": <0-20の整数>,  // 影響の引き出し
  "value_proposition": <0-20の整数>,  // 価値提案の的確さ
  "customer_response": <0-20の整数>,  // 顧客の反応と整合性
  "advancement": <0-20の整数>,  // 商談前進度
  "total": <5要素の合計値（0-100）>,
  "feedback": "<フィードバック文（200-300文字）>",
  "next_actions": "<次回アクション（100-200文字）>",
  "scoring_details": {{
    "exploration": {{
      "score": <0-20の整数>,
      "comments": "<コメント>",
      "strengths": ["強み1", "強み2"],
      "weaknesses": ["弱み1", "弱み2"]
    }},
    "implication": {{
      "score": <0-20の整数>,
      "comments": "<コメント>",
      "strengths": ["強み1"],
      "weaknesses": ["弱み1"]
    }},
    "value_proposition": {{
      "score": <0-20の整数>,
      "comments": "<コメント>",
      "strengths": ["強み1"],
      "weaknesses": ["弱み1"]
    }},
    "customer_response": {{
      "score": <0-20の整数>,
      "comments": "<コメント>",
      "strengths": ["強み1"],
      "weaknesses": ["弱み1"]
    }},
    "advancement": {{
      "score": <0-20の整数>,
      "comments": "<コメント>",
      "strengths": ["強み1"],
      "weaknesses": ["弱み1"]
    }}
  }},
  // 後方互換性のため、SPIN要素も含める（探索力と影響の引き出しから算出）
  "situation": <探索力から算出>,
  "problem": <探索力から算出>,
  "implication": <影響の引き出しから算出>,
  "need": <価値提案の的確さから算出>
}}
"""
    
    try:
        messages = [
            {"role": "system", "content": "あなたは営業スキル評価の専門家です。必ずJSON形式で回答してください。"},
            {"role": "user", "content": prompt},
        ]
        
        # response_formatは一部のモデルのみサポート（gpt-4-turbo, gpt-4o, gpt-3.5-turbo-1106以降など）
        # gpt-4（旧モデル）ではサポートされていないため、条件付きで使用
        kwargs = {}
        # モデルIDで判定（response_formatをサポートするモデルのみ）
        supports_json_mode = any(
            model_id in model.model_id.lower() 
            for model_id in ['gpt-4-turbo', 'gpt-4o', 'gpt-3.5-turbo-1106', 'gpt-3.5-turbo-0125', 'gpt-4-0125', 'gpt-4-1106']
        )
        
        if supports_json_mode:
            kwargs['response_format'] = {"type": "json_object"}
        else:
            # response_formatが使えない場合は、プロンプトでJSON形式を強く要求
            messages[0]["content"] = "あなたは営業スキル評価の専門家です。必ずJSON形式で回答してください。他の形式は一切使用しないでください。"
        
        response_content, usage = client.chat_completion(
            model=model,
            messages=messages,
            temperature=0.7,
            **kwargs
        )
        
        if not response_content:
            raise ValueError("AIからの応答が空です")
        
        logger.info(
            f"スコアリング完了: Session {session.id}, mode={session.mode}, "
            f"provider={model.provider}, model={model_name}, "
            f"tokens={usage.get('total_tokens', 0) if usage else 'N/A'}"
        )
        return response_content
    except Exception as e:
        logger.error(f"スコアリングエラー: Session {session.id}, Error: {str(e)}", exc_info=True)
        raise

