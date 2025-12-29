"""
Text-to-Speech サービス
OpenAI TTS APIを使用してテキストを音声に変換
"""
import logging
from typing import Optional, Tuple
from io import BytesIO

logger = logging.getLogger(__name__)

# 利用可能な音声タイプ
AVAILABLE_VOICES = {
    'alloy': {'name': 'Alloy', 'gender': 'neutral', 'description': 'バランスの取れた中性的な声'},
    'echo': {'name': 'Echo', 'gender': 'male', 'description': '落ち着いた男性の声'},
    'fable': {'name': 'Fable', 'gender': 'male', 'description': 'イギリス英語風、物語調'},
    'onyx': {'name': 'Onyx', 'gender': 'male', 'description': '低めの男性の声、権威的'},
    'nova': {'name': 'Nova', 'gender': 'female', 'description': '明るく親しみやすい女性の声'},
    'shimmer': {'name': 'Shimmer', 'gender': 'female', 'description': '柔らかく温かみのある女性の声'},
}

# デフォルト音声
DEFAULT_VOICE = 'nova'


def get_voice_for_persona(persona: str) -> str:
    """
    顧客ペルソナから適切な音声を自動選択
    
    Args:
        persona: 顧客ペルソナの説明文字列
    
    Returns:
        str: 音声ID ('nova', 'shimmer', 'onyx', 'echo', 'alloy')
    """
    if not persona:
        return DEFAULT_VOICE
    
    persona_lower = persona.lower()
    
    # 女性キーワード
    female_keywords = ['女性', '女', 'レディ', 'ウーマン', '彼女', '奥様', '夫人', '嬢']
    # 男性キーワード
    male_keywords = ['男性', '男', 'メン', '紳士', '彼', '氏', '殿']
    # 経営者・上位職キーワード
    executive_keywords = ['社長', '経営', 'CEO', '代表', '役員', '取締役', '部長', 'マネージャー', '責任者', 'オーナー']
    
    is_female = any(kw in persona_lower for kw in female_keywords)
    is_male = any(kw in persona_lower for kw in male_keywords)
    is_executive = any(kw in persona_lower for kw in executive_keywords)
    
    if is_female:
        if is_executive:
            return 'nova'  # 明るく自信のある女性経営者
        return 'shimmer'  # 柔らかい女性担当者
    elif is_male:
        if is_executive:
            return 'onyx'  # 権威的な男性経営者
        return 'echo'  # 落ち着いた男性担当者
    else:
        return 'alloy'  # 中性的なデフォルト


def generate_speech(
    text: str,
    voice: str = DEFAULT_VOICE,
    model: str = 'tts-1',
    speed: float = 1.0,
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    テキストを音声に変換
    
    Args:
        text: 変換するテキスト
        voice: 音声タイプ ('alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer')
        model: TTSモデル ('tts-1' または 'tts-1-hd')
        speed: 再生速度 (0.25 - 4.0)
    
    Returns:
        Tuple[bytes, str]: (音声データ, エラーメッセージ)
        成功時は (音声データ, None)
        失敗時は (None, エラーメッセージ)
    """
    from spin.services.ai_provider_factory import AIProviderFactory
    from spin.models import AIProviderKey
    
    if not text or not text.strip():
        return None, "テキストが空です"
    
    # 音声タイプのバリデーション
    if voice not in AVAILABLE_VOICES:
        voice = DEFAULT_VOICE
    
    # 速度のバリデーション
    speed = max(0.25, min(4.0, speed))
    
    try:
        # OpenAI APIキーを取得
        provider_key = AIProviderKey.objects.filter(
            provider='openai',
            is_active=True
        ).order_by('-is_default', '-created_at').first()
        
        if not provider_key:
            return None, "OpenAI APIキーが設定されていません"
        
        # OpenAIクライアントを作成
        from openai import OpenAI
        client = OpenAI(api_key=provider_key.api_key)
        
        # TTS APIを呼び出し
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            speed=speed,
            response_format='mp3',
        )
        
        # 音声データを取得
        audio_data = response.content
        
        logger.info(
            f"TTS生成成功: voice={voice}, model={model}, "
            f"text_length={len(text)}, audio_size={len(audio_data)} bytes"
        )
        
        return audio_data, None
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"TTS生成エラー: {error_msg}", exc_info=True)
        return None, f"音声生成に失敗しました: {error_msg}"


def get_available_voices():
    """利用可能な音声の一覧を取得"""
    return [
        {
            'id': voice_id,
            'name': voice_info['name'],
            'gender': voice_info['gender'],
            'description': voice_info['description'],
        }
        for voice_id, voice_info in AVAILABLE_VOICES.items()
    ]

