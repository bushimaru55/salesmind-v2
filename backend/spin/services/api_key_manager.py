"""
OpenAI APIキー管理サービス
用途別・モデル別にAPIキーを取得する
"""
import logging
from typing import Optional, Tuple
from spin.models import OpenAIAPIKey, ModelConfiguration, AIProviderKey

logger = logging.getLogger(__name__)


class APIKeyManager:
    """APIキー管理クラス"""
    
    @staticmethod
    def get_api_key_and_model(purpose: str = 'general') -> Tuple[Optional[str], Optional[str]]:
        """
        用途に応じたAPIキーとモデル名を取得
        
        優先順位:
        1. ModelConfigurationで設定されたプロバイダーキー + モデル（最優先）
        2. AIProviderKey（新システム）
        3. OpenAIAPIKey（レガシー）
        
        Args:
            purpose: APIキーの用途 ('spin_generation', 'chat', 'scoring', 'scraping_analysis', 'general')
        
        Returns:
            Tuple[api_key, model_name]: APIキーとモデル名のタプル
            見つからない場合は (None, None)
        """
        try:
            # 1. ModelConfigurationから設定を取得（最優先）
            try:
                model_config = ModelConfiguration.objects.get(purpose=purpose, is_active=True)
                
                # primary_provider_keyからAPIキーを取得
                if model_config.primary_provider_key and model_config.primary_provider_key.is_active:
                    api_key = model_config.primary_provider_key.api_key
                    
                    # モデル名を取得
                    model_name = None
                    if model_config.primary_model:
                        model_name = model_config.primary_model.model_id
                    elif model_config.legacy_model_name:
                        model_name = model_config.legacy_model_name
                    else:
                        model_name = 'gpt-4o-mini'  # デフォルト
                    
                    logger.info(f"ModelConfigurationからAPIキーとモデルを取得: purpose={purpose}, model={model_name}")
                    return api_key, model_name
                    
            except ModelConfiguration.DoesNotExist:
                logger.debug(f"ModelConfigurationが見つかりません: purpose={purpose}")
            
            # 2. AIProviderKey（新システム）からOpenAIキーを探す
            provider_key = AIProviderKey.objects.filter(
                provider='openai',
                is_active=True
            ).first()
            
            if provider_key:
                # ModelConfigurationからモデル名を取得（あれば）
                model_name = 'gpt-4o-mini'  # デフォルト
                try:
                    model_config = ModelConfiguration.objects.get(purpose=purpose, is_active=True)
                    if model_config.primary_model:
                        model_name = model_config.primary_model.model_id
                    elif model_config.legacy_model_name:
                        model_name = model_config.legacy_model_name
                except ModelConfiguration.DoesNotExist:
                    pass
                
                logger.info(f"AIProviderKeyからAPIキーを取得: purpose={purpose}, model={model_name}")
                return provider_key.api_key, model_name
            
            # 3. レガシー: OpenAIAPIKeyから探す
            api_key_obj = OpenAIAPIKey.objects.filter(
                purpose=purpose,
                is_active=True,
                is_default=True
            ).first()
            
            if not api_key_obj:
                api_key_obj = OpenAIAPIKey.objects.filter(
                    purpose=purpose,
                    is_active=True
                ).first()
            
            if not api_key_obj:
                api_key_obj = OpenAIAPIKey.objects.filter(
                    purpose='general',
                    is_active=True
                ).first()
            
            if api_key_obj:
                logger.info(
                    f"OpenAIAPIKeyからAPIキー取得成功: purpose={purpose}, "
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

