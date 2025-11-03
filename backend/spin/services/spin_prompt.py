"""
SPIN質問生成用プロンプトテンプレート
"""


def build_spin_generation_prompt(industry, value_proposition, customer_persona=None, customer_pain=None):
    """SPIN質問生成用プロンプトを構築"""
    prompt = f"""
あなたはB2B営業コーチです。以下の情報を基に、SPIN思考に基づいた営業質問を生成してください。

業界: {industry}
価値提案: {value_proposition}
"""
    if customer_persona:
        prompt += f"顧客像: {customer_persona}\n"
    if customer_pain:
        prompt += f"顧客の課題: {customer_pain}\n"
    
    prompt += """
SPIN各要素（Situation, Problem, Implication, Need）ごとに、実際の商談で使用できる質問を3〜5個ずつ日本語で生成してください。
各質問は自然で、顧客の状況を深掘りできるものにしてください。
"""
    return prompt

