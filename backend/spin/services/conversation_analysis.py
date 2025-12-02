import json
import logging
import os
from typing import Dict, List

from openai import OpenAI
from ..utils import get_openai_api_key


logger = logging.getLogger(__name__)


def get_client():
    """OpenAIクライアントを取得（会話分析用）"""
    try:
        api_key = get_openai_api_key(purpose='chat')
        return OpenAI(api_key=api_key)
    except Exception as e:
        logger.error(f"OpenAIクライアント取得エラー: Error: {str(e)}")
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _format_conversation(messages: List[Dict[str, str]], limit: int = 10) -> str:
    """会話履歴をOpenAIに渡すために整形"""
    trimmed = messages[-limit:]
    lines = []
    for msg in trimmed:
        role_label = "営業" if msg.get("role") == "salesperson" else "顧客"
        content = msg.get("message", "").strip()
        lines.append(f"{role_label}: {content}")
    return "\n".join(lines)


def analyze_sales_message(session, conversation_history, latest_message: str) -> Dict[str, any]:
    """営業メッセージを分析し、成功率変動を算出"""
    logger.info(f"会話分析開始: Session {session.id}, 現在の成功率={session.success_probability}%")
    
    logger.info(
        "会話分析入力: session=%s, current_probability=%s, history_count=%s, latest_message_length=%s",
        session.id,
        session.success_probability,
        len(conversation_history),
        len(latest_message),
    )

    formatted_history = _format_conversation(
        [{"role": msg.role, "message": msg.message} for msg in conversation_history]
    )

    # 企業情報を詳細に取得
    company_info_text = ""
    if session.company:
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
        if company.scraped_data and company.scraped_data.get('text_content'):
            text_content = company.scraped_data.get('text_content', '')[:2000]
            company_lines.append(f"\n--- Webサイト情報（抜粋） ---")
            company_lines.append(text_content)
        
        company_info_text = "\n".join(company_lines)
    else:
        company_info_text = "（企業情報なし）"

    prompt = f"""【役割定義】
あなたは「会話分析AI」です。
・入力は営業担当者（ユーザー）の発言のみを対象にすること。
・顧客の発言は分析対象に含めない。
・顧客の発言は参照するが、分類対象ではない。

あなたはB2B営業のメンターとして、直近の営業担当者（ユーザー）の発言が商談成功に与える影響を分析してください。

--- セッション情報（営業文脈の基準） ---
業界: {session.industry}
価値提案: {session.value_proposition}
顧客像: {session.customer_persona or '未設定'}
現在の商談成功率: {session.success_probability}%

--- 企業情報（実際の顧客企業） ---
{company_info_text}

--- 会話履歴（最近） ---
{formatted_history}
※注意：会話履歴は参考情報として提供しますが、分析対象は「営業担当者の発言」のみです。

--- 今回の営業担当者の発言（分析対象） ---
{latest_message}
---

【営業意図分類】
上記の「今回の営業担当者の発言」のみを次のどれかに分類してください：
- S（状況質問）: 顧客の現状・背景を確認する質問
- P（問題質問）: 顧客の課題を顕在化させる質問
- I（示唆）: 課題が放置された場合の影響を示唆する質問
- N（価値訴求）: 解決後の価値やメリットを想像させる質問
- 雑談: 営業に関連しない会話
- クロージング意図: 見積・デモ・契約などの次のステップを促す発言
- 商談終了意図: 商談を終了させようとする発言
- 関連性の薄い提案: 業界・価値提案と関連性が低い提案
- 強引・不適切な提案: 強引・唐突・不合理な提案

【重要】顧客の発言は分類対象ではありません。営業担当者の発言のみを分類してください。

分類結果は内部ロジックに使用し、会話には直接返さない。

【目的】
- 営業担当者の発言をSPIN段階に分類し、state.phase を更新する
- 営業担当者の発言の質を評価し、成功率変動を算出する

【評価方針 - SPIN法に基づく評価】

1. 現在の会話段階の判定
   - S（Situation）: 顧客の現状・背景を確認する段階
   - P（Problem）: 顧客の課題を顕在化させる段階
   - I（Implication）: 課題が放置された場合の影響を示唆する段階
   - N（Need-Payoff）: 解決後の価値やメリットを想像させる段階
   - 判定が難しい場合は "unknown" と記載

2. 今回の営業担当者の発言がどのステップに該当するか判定（S/P/I/N いずれか。判定不能は "unknown"）

3. ステップ適切性の評価
   - ideal: S→P→I→N と理想的に進行し、現在の段階に適合している
   - appropriate: 現段階に適切だが理想的な進行とは言えない
   - jump: 必要な前段階を飛ばしている
   - regression: 後段階から前段階に逆戻りしている
   - 判断不能の場合は "unknown"

4. 各ステップの質を評価
   - S: 企業情報を活用した具体的な状況確認になっているか
   - P: 顧客の課題を自然に引き出せているか
   - I: 課題放置のリスクや影響を顧客に認識させられているか
   - N: 解決後の価値を顧客自身にイメージさせられているか

5. 成功率変動の算出ルール（SPIN順番ペナルティを弱くする）
   - 理想的な進行で質の高い質問: +4〜+5
   - 適切なステップで良い質問: +2〜+3
   - 通常レベルの質問: +1〜+2（内容が良ければ加点）
   - 段階の飛び越し・逆戻り: -1〜0（軽微なペナルティのみ、内容が良ければ0点）
   - 不適切・話題逸脱: -3〜-1（内容が良ければ軽減）
   - **重要**: SPIN順番がズレても、内容が良ければ高得点維持。最重要は「深掘りの質」「顧客反応との整合性」。
   - **注意**: 常に0を返すのではなく、上記基準に従いプラス／マイナスを積極的に判断してください。

成功率変動を決定する際は、以下の視点を必ず考慮してください：
- 現在の会話段階と今回の発言段階の整合性
- 営業担当者の発言が顧客の反応を引き出す深さや具体性
- 価値提案や企業情報との関連度
- 営業担当者の発言に顧客視点・共感が表れているか

【重要】顧客の発言は参照情報として使用しますが、分析対象は「営業担当者の発言」のみです。
顧客の反応が良くても悪くても、営業担当者の発言の質を評価してください。

出力フォーマットは必ず次のJSON形式（各キーは必須）で出力してください：
{{
  "current_spin_stage": "S" または "P" または "I" または "N" または "unknown",
  "message_spin_type": "S" または "P" または "I" または "N" または "unknown",
  "step_appropriateness": "ideal" または "appropriate" または "jump" または "regression" または "unknown",
  "success_delta": 整数 (-5〜5),
  "reason": "今回の変動理由（SPINの観点を含む1〜2文）",
  "notes": "補足があれば（任意、無い場合は空文字）"
}}

success_deltaは-5〜5の整数で、プラスは成功率を上げる要素、マイナスは下げる要素を意味します。
"""

    try:
        client = get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "あなたはB2B営業メンターです。必ずJSON形式で返答してください。"
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        payload = response.choices[0].message.content
        logger.info("会話分析レスポンス: %s", payload)
        result = json.loads(payload)

        success_delta = int(result.get("success_delta", 0))
        # クランプ処理
        success_delta = max(-5, min(5, success_delta))

        current_stage = result.get("current_spin_stage")
        message_stage = result.get("message_spin_type")
        step_appropriateness = result.get("step_appropriateness")

        valid_spin_values = {"S", "P", "I", "N"}
        valid_step_values = {"ideal", "appropriate", "jump", "regression"}

        normalized_stage = current_stage if current_stage in valid_spin_values else "unknown"
        normalized_message_stage = message_stage if message_stage in valid_spin_values else "unknown"
        normalized_step = step_appropriateness if step_appropriateness in valid_step_values else "unknown"

        logger.info(
            "会話分析結果: delta=%s, stage_raw=%s, stage=%s, message_raw=%s, message=%s, step_raw=%s, step=%s",
            success_delta,
            current_stage,
            normalized_stage,
            message_stage,
            normalized_message_stage,
            step_appropriateness,
            normalized_step,
        )

        return {
            "current_spin_stage": normalized_stage,
            "message_spin_type": normalized_message_stage,
            "step_appropriateness": normalized_step,
            "success_delta": success_delta,
            "reason": result.get("reason", ""),
            "notes": result.get("notes"),
        }
    except Exception as exc:
        logger.warning("会話分析に失敗しました: %s", exc, exc_info=True)
        return {
            "current_spin_stage": "unknown",
            "message_spin_type": "unknown",
            "step_appropriateness": "unknown",
            "success_delta": 0,
            "reason": "分析を実行できなかったため成功率は変化しませんでした。",
            "notes": None,
        }

