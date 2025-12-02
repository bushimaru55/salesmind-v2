"""
ユーティリティ関数
"""
import os
from .models import OpenAIAPIKey


def get_openai_api_key(purpose=None):
    """
    OpenAI APIキーを取得
    
    優先順位:
    1. DB内の有効で指定用途のデフォルトキー
    2. DB内の有効で指定用途の最新キー
    3. DB内の有効な汎用デフォルトキー
    4. DB内の有効な汎用キー
    5. 環境変数 OPENAI_API_KEY
    
    Args:
        purpose (str, optional): APIキーの用途
            - 'spin_generation': SPIN質問生成
            - 'chat': チャット（顧客役）
            - 'scoring': スコアリング
            - 'scraping_analysis': スクレイピング分析
            - 'general': 汎用
    
    Returns:
        str: OpenAI APIキー
    
    Raises:
        ValueError: APIキーが見つからない場合
    """
    try:
        # 1. 指定用途のデフォルトキー
        if purpose:
            key_obj = OpenAIAPIKey.objects.filter(
                purpose=purpose,
                is_active=True,
                is_default=True
            ).first()
            
            if key_obj:
                return key_obj.api_key
            
            # 2. 指定用途の最新キー
            key_obj = OpenAIAPIKey.objects.filter(
                purpose=purpose,
                is_active=True
            ).first()
            
            if key_obj:
                return key_obj.api_key
        
        # 3. 汎用デフォルトキー
        key_obj = OpenAIAPIKey.objects.filter(
            purpose='general',
            is_active=True,
            is_default=True
        ).first()
        
        if key_obj:
            return key_obj.api_key
        
        # 4. 汎用キー
        key_obj = OpenAIAPIKey.objects.filter(
            purpose='general',
            is_active=True
        ).first()
        
        if key_obj:
            return key_obj.api_key
        
        # 5. 環境変数
        env_key = os.environ.get('OPENAI_API_KEY')
        if env_key:
            return env_key
        
        # APIキーが見つからない
        raise ValueError(
            "OpenAI APIキーが見つかりません。"
            "管理画面からAPIキーを登録するか、環境変数 OPENAI_API_KEY を設定してください。"
        )
    
    except Exception as e:
        # DB接続エラーなどの場合は環境変数にフォールバック
        env_key = os.environ.get('OPENAI_API_KEY')
        if env_key:
            return env_key
        raise e


def get_all_active_api_keys():
    """
    すべての有効なAPIキーを取得（用途別）
    
    Returns:
        dict: {purpose: api_key}
    """
    keys = {}
    try:
        for key_obj in OpenAIAPIKey.objects.filter(is_active=True):
            if key_obj.purpose not in keys:
                keys[key_obj.purpose] = key_obj.api_key
    except Exception:
        pass
    
    return keys

