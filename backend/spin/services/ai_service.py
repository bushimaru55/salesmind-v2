"""
AI統合サービス
複数のAIプロバイダーを統合的に管理し、用途に応じて最適なプロバイダー/モデルを使用
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from spin.services.ai_provider_factory import AIProviderFactory, BaseAIClient
from spin.models import AIModel, ModelConfiguration

logger = logging.getLogger(__name__)


class AIService:
    """AI統合サービスクラス"""
    
    @staticmethod
    def chat_completion(
        purpose: str,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        チャット補完（用途に応じて最適なプロバイダー/モデルを使用）
        
        Args:
            purpose: 用途（'spin_generation', 'chat', 'scoring', 'scraping_analysis'）
            messages: メッセージリスト
            temperature: Temperature（Noneの場合は設定から取得）
            max_tokens: 最大トークン数
            **kwargs: その他のパラメータ
        
        Returns:
            Tuple[str, Dict]: (応答テキスト, 使用量情報)
            エラーの場合は (None, None)
        """
        try:
            # 設定を取得
            config = ModelConfiguration.get_config_for_purpose(purpose)
            if not config:
                logger.error(f"No configuration found for purpose: {purpose}")
                return None, None
            
            # Temperatureが指定されていない場合は設定から取得
            if temperature is None:
                temperature = float(config.temperature)
            
            # クライアントとモデルを取得
            client, model = AIProviderFactory.get_client_and_model_for_purpose(purpose)
            
            if not client or not model:
                logger.error(f"No available client/model for purpose: {purpose}")
                return None, None
            
            # チャット補完を実行
            content, usage = client.chat_completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            logger.info(
                f"Chat completion success: purpose={purpose}, "
                f"provider={model.provider}, model={model.model_id}, "
                f"tokens={usage.get('total_tokens', 0)}"
            )
            
            return content, usage
        
        except Exception as e:
            logger.error(f"Chat completion error: {e}", exc_info=True)
            return None, None
    
    @staticmethod
    def test_provider_connection(provider_key_id: str) -> Dict[str, Any]:
        """
        プロバイダーの接続テスト
        
        Args:
            provider_key_id: AIProviderKeyのID
        
        Returns:
            Dict: {'success': bool, 'message': str, 'model': str (optional)}
        """
        try:
            from spin.models import AIProviderKey
            
            provider_key = AIProviderKey.objects.get(id=provider_key_id)
            client = AIProviderFactory.create_client(provider_key)
            
            result = client.test_connection()
            logger.info(f"Connection test: provider={provider_key.provider}, result={result}")
            
            return result
        
        except Exception as e:
            logger.error(f"Connection test error: {e}")
            return {
                'success': False,
                'message': f'接続テストエラー: {str(e)}'
            }
    
    @staticmethod
    def get_available_models_for_provider(provider: str) -> List[AIModel]:
        """
        プロバイダーで利用可能なモデル一覧を取得
        
        Args:
            provider: プロバイダー名（'openai', 'anthropic', 'google'）
        
        Returns:
            List[AIModel]: モデルのリスト
        """
        return AIModel.objects.filter(provider=provider, is_active=True).order_by('model_id')
    
    @staticmethod
    def get_recommended_models_for_purpose(purpose: str) -> List[AIModel]:
        """
        用途に推奨されるモデル一覧を取得
        
        Args:
            purpose: 用途（'spin_generation', 'chat', 'scoring', 'scraping_analysis'）
        
        Returns:
            List[AIModel]: 推奨モデルのリスト
        """
        filters = {}
        
        if purpose == 'spin_generation':
            filters['recommended_for_generation'] = True
        elif purpose == 'chat':
            filters['recommended_for_chat'] = True
        elif purpose == 'scoring':
            filters['recommended_for_scoring'] = True
        elif purpose == 'scraping_analysis':
            filters['recommended_for_analysis'] = True
        
        return AIModel.objects.filter(**filters, is_active=True).order_by('input_cost_per_1m')
    
    @staticmethod
    def estimate_cost(
        model_id: str,
        provider: str,
        input_tokens: int,
        output_tokens: int
    ) -> Optional[float]:
        """
        コストを推定
        
        Args:
            model_id: モデルID
            provider: プロバイダー名
            input_tokens: 入力トークン数
            output_tokens: 出力トークン数
        
        Returns:
            float: 推定コスト（USD）、情報がない場合はNone
        """
        try:
            model = AIModel.objects.get(provider=provider, model_id=model_id)
            cost = model.get_estimated_cost(input_tokens, output_tokens)
            return float(cost)
        except AIModel.DoesNotExist:
            logger.warning(f"Model not found: {provider}/{model_id}")
            return None

