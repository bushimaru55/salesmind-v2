"""
企業情報分析機能
スクレイピングした企業情報を元に、OpenAIを使用してSPIN提案適合性を分析する
"""
import logging
import os
import json
from openai import OpenAI
from typing import Dict, Any

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_spin_suitability(company_info: Dict[str, Any], value_proposition: str) -> Dict[str, Any]:
    """
    企業情報と価値提案を元に、SPIN法に基づく提案適合性を分析
    
    Args:
        company_info: 企業情報の辞書
        value_proposition: 価値提案
    
    Returns:
        SPIN適合性分析結果の辞書
    """
    logger.info(f"SPIN適合性分析を開始: 企業={company_info.get('company_name', 'Unknown')}")
    
    # 企業情報をテキストに変換
    company_text = format_company_info(company_info)
    
    prompt = f"""
あなたは営業提案の専門家です。以下の企業情報と価値提案を元に、SPIN法に基づく営業提案の適合性を分析してください。

【企業情報】
{company_text}

【価値提案】
{value_proposition}

以下の観点から分析してください：

1. **Situation（状況確認）**
   - この企業に対して状況確認の質問ができるか？
   - 企業情報から状況を把握できるか？
   - スコア: 0-100点

2. **Problem（問題発見）**
   - この企業の潜在的な課題は何か？
   - 問題発見の質問ができるか？
   - スコア: 0-100点

3. **Implication（示唆）**
   - 課題の影響範囲を推測できるか？
   - 示唆の質問ができるか？
   - スコア: 0-100点

4. **Need（ニーズ確認）**
   - 価値提案が企業のニーズと適合するか？
   - ニーズ確認の質問ができるか？
   - スコア: 0-100点

以下のJSON形式で回答してください：
{{
  "spin_suitability": {{
    "situation": {{
      "score": <0-100の整数>,
      "can_ask": <true/false>,
      "reason": "<理由>"
    }},
    "problem": {{
      "score": <0-100の整数>,
      "can_ask": <true/false>,
      "potential_problems": ["課題1", "課題2"],
      "reason": "<理由>"
    }},
    "implication": {{
      "score": <0-100の整数>,
      "can_ask": <true/false>,
      "estimated_impact": "<影響度>",
      "reason": "<理由>"
    }},
    "need": {{
      "score": <0-100の整数>,
      "can_ask": <true/false>,
      "reason": "<理由>"
    }}
  }},
  "recommendations": {{
    "proposal_approach": "<推奨される提案アプローチ>",
    "key_questions": ["質問1", "質問2", "質問3"],
    "warnings": ["警告1", "警告2"]
  }}
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは営業提案の専門家です。必ずJSON形式で回答してください。"},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        
        response_content = response.choices[0].message.content
        analysis_result = json.loads(response_content)
        
        logger.info(f"SPIN適合性分析が完了: 企業={company_info.get('company_name', 'Unknown')}")
        return analysis_result
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析エラー: {e}", exc_info=True)
        raise ValueError(f"分析結果のJSON解析に失敗しました: {e}")
    except Exception as e:
        logger.error(f"SPIN適合性分析エラー: {e}", exc_info=True)
        raise ValueError(f"SPIN適合性分析に失敗しました: {e}")


def format_company_info(company_info: Dict[str, Any]) -> str:
    """
    企業情報をテキスト形式にフォーマット
    
    Args:
        company_info: 企業情報の辞書
    
    Returns:
        フォーマットされたテキスト
    """
    lines = []
    
    if company_info.get('company_name'):
        lines.append(f"会社名: {company_info['company_name']}")
    if company_info.get('industry'):
        lines.append(f"業界: {company_info['industry']}")
    if company_info.get('business_description'):
        lines.append(f"事業内容: {company_info['business_description']}")
    if company_info.get('location'):
        lines.append(f"所在地: {company_info['location']}")
    if company_info.get('employee_count'):
        lines.append(f"従業員数: {company_info['employee_count']}")
    if company_info.get('established_year'):
        lines.append(f"設立年: {company_info['established_year']}")
    
    # raw_html_listがある場合、最初のものを含める
    if company_info.get('raw_html_list'):
        lines.append(f"\n【スクレイピングしたコンテンツ（一部）】")
        lines.append(company_info['raw_html_list'][0][:2000])  # 最初の2000文字
    
    return "\n".join(lines)

