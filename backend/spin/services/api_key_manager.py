"""
OpenAI APIキー管理サービス
用途別・モデル別にAPIキーを取得する
"""
import logging
from typing import Optional, Tuple
from spin.models import OpenAIAPIKey, ModelConfiguration

logger = logging.getLogger(__name__)


class APIKeyManager:
    """APIキー管理クラス"""
    
    @staticmethod
    def get_api_key_and_model(purpose: str = 'general') -> Tuple[Optional[str], Optional[str]]:
        """
        用途に応じたAPIキーとモデル名を取得
        
        優先順位:
        1. ModelConfigurationで設定されたモデル（最優先）
        2. 指定された用途のデフォルトAPIキー
        3. 指定された用途の有効なAPIキー
        4. 汎用のデフォルトAPIキー
        5. 汎用の有効なAPIキー
        
        Args:
            purpose: APIキーの用途 ('spin_generation', 'chat', 'scoring', 'scraping_analysis', 'general')
        
        Returns:
            Tuple[api_key, model_name]: APIキーとモデル名のタプル
            見つからない場合は (None, None)
        """
        try:
            # 0. ModelConfigurationから推奨モデルを取得（最優先）
            preferred_model = None
            try:
                model_config = ModelConfiguration.objects.get(purpose=purpose, is_active=True)
                preferred_model = model_config.model_name
                logger.info(f"ModelConfigurationから推奨モデルを取得: purpose={purpose}, model={preferred_model}")
            except ModelConfiguration.DoesNotExist:
                # ModelConfigurationがない場合は、デフォルトの推奨モデルを使用
                preferred_model = ModelConfiguration.RECOMMENDED_MODELS.get(purpose)
                if preferred_model:
                    logger.info(f"デフォルト推奨モデルを使用: purpose={purpose}, model={preferred_model}")
            
            # 推奨モデルが設定されている場合、そのモデルを使用するAPIキーを優先的に探す
            if preferred_model:
                # 推奨モデルを使用する有効なAPIキーを探す
                api_key_obj = OpenAIAPIKey.objects.filter(
                    purpose=purpose,
                    model_name=preferred_model,
                    is_active=True
                ).first()
                
                if api_key_obj:
                    logger.info(
                        f"推奨モデルのAPIキー取得成功: purpose={purpose}, "
                        f"key_name={api_key_obj.name}, model={api_key_obj.model_name}"
                    )
                    return api_key_obj.api_key, api_key_obj.model_name
                else:
                    logger.warning(
                        f"推奨モデル({preferred_model})のAPIキーが見つかりません。"
                        f"他のモデルを使用します: purpose={purpose}"
                    )
            
            # 推奨モデルのAPIキーがない場合、従来の方法でAPIキーを探す
            # 1. 指定された用途のデフォルトキーを探す
            api_key_obj = OpenAIAPIKey.objects.filter(
                purpose=purpose,
                is_active=True,
                is_default=True
            ).first()
            
            # 2. デフォルトキーがなければ、指定された用途の有効なキーを探す
            if not api_key_obj:
                api_key_obj = OpenAIAPIKey.objects.filter(
                    purpose=purpose,
                    is_active=True
                ).first()
            
            # 3. それでもなければ、汎用のデフォルトキーを探す
            if not api_key_obj:
                api_key_obj = OpenAIAPIKey.objects.filter(
                    purpose='general',
                    is_active=True,
                    is_default=True
                ).first()
            
            # 4. 最後の手段として、汎用の有効なキーを探す
            if not api_key_obj:
                api_key_obj = OpenAIAPIKey.objects.filter(
                    purpose='general',
                    is_active=True
                ).first()
            
            if api_key_obj:
                logger.info(
                    f"APIキー取得成功: purpose={purpose}, "
                    f"key_name={api_key_obj.name}, model={api_key_obj.model_name}"
                )
                return api_key_obj.api_key, api_key_obj.model_name
            
            logger.error(f"有効なAPIキーが見つかりません: purpose={purpose}")
            return None, None
            
        except Exception as e:
            logger.error(f"APIキー取得エラー: {str(e)}")
            return None, None
    
    @staticmethod
    def get_api_key_for_spin_generation() -> Tuple[Optional[str], Optional[str]]:
        """SPIN質問生成用のAPIキーとモデルを取得"""
        return APIKeyManager.get_api_key_and_model('spin_generation')
    
    @staticmethod
    def get_api_key_for_chat() -> Tuple[Optional[str], Optional[str]]:
        """チャット（顧客役）用のAPIキーとモデルを取得"""
        return APIKeyManager.get_api_key_and_model('chat')
    
    @staticmethod
    def get_api_key_for_scoring() -> Tuple[Optional[str], Optional[str]]:
        """スコアリング用のAPIキーとモデルを取得"""
        return APIKeyManager.get_api_key_and_model('scoring')
    
    @staticmethod
    def get_api_key_for_scraping_analysis() -> Tuple[Optional[str], Optional[str]]:
        """スクレイピング分析用のAPIキーとモデルを取得"""
        return APIKeyManager.get_api_key_and_model('scraping_analysis')
    
    @staticmethod
    def get_default_api_key() -> Tuple[Optional[str], Optional[str]]:
        """デフォルトのAPIキーとモデルを取得"""
        return APIKeyManager.get_api_key_and_model('general')
    
    @staticmethod
    def validate_api_key_exists(purpose: str = 'general') -> bool:
        """
        指定された用途のAPIキーが存在するか確認
        
        Args:
            purpose: APIキーの用途
        
        Returns:
            bool: APIキーが存在する場合True
        """
        api_key, model = APIKeyManager.get_api_key_and_model(purpose)
        return api_key is not None and model is not None

