"""
SPIN質問生成用プロンプトテンプレート（業界特化版）
"""


def build_spin_generation_prompt(industry, value_proposition, customer_persona=None, customer_pain=None):
    """
    SPIN質問生成用のプロンプトを構築（業界特化版）
    
    業界・価値提案・顧客像を軸に、業界特化の質問を生成する。
    """
    prompt = f"""
あなたはSPINメソッドの質問生成AIです。
以下の商談設定に基づき、業界特化の質問を生成してください。

【業界】{industry}
【価値提案】{value_proposition}
"""
    if customer_persona:
        prompt += f"【顧客像】{customer_persona}\n"
    if customer_pain:
        prompt += f"【顧客の課題】{customer_pain}\n"
    
    prompt += f"""
【質問生成方針】
・業界「{industry}」固有の課題を織り交ぜる
・価値提案「{value_proposition}」が自然に想起される質問設計
・顧客像に応じてレイヤー（社長／部長／担当者）を調整
・業界「{industry}」の特性を考慮した具体的な質問を生成する

SPIN各要素（Situation, Problem, Implication, Need）ごとに、実際の商談で使用できる質問を3〜5個ずつ日本語で生成してください。
各質問は自然で、顧客の状況を深掘りできるものにしてください。

以下のJSON形式で返してください：
{{
  "situation": ["質問1", "質問2", "質問3"],
  "problem": ["質問1", "質問2", "質問3"],
  "implication": ["質問1", "質問2", "質問3"],
  "need": ["質問1", "質問2", "質問3"]
}}
"""
    return prompt
