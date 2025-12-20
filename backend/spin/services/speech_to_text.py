"""
GCP Speech-to-Text APIを使用した音声認識サービス
"""
import logging
import os
from typing import Dict, Any, Optional
from google.cloud import speech
from google.oauth2 import service_account
import io
import tempfile

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("pydub library is not installed. Audio conversion will not be available.")

if 'logger' not in locals():
    logger = logging.getLogger(__name__)


def get_speech_client() -> Optional[speech.SpeechClient]:
    """
    GCP Speech-to-Text APIクライアントを取得
    
    Returns:
        SpeechClient: GCP Speech-to-Text APIクライアント
        None: 認証情報が設定されていない場合
    """
    try:
        # 環境変数からサービスアカウントキーのパスを取得
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if credentials_path:
            # 相対パスの場合は絶対パスに変換（Django settingsのBASE_DIRを基準に）
            if not os.path.isabs(credentials_path):
                # Django settingsからPROJECT_ROOTを取得
                from django.conf import settings
                if hasattr(settings, 'BASE_DIR'):
                    # BASE_DIRはbackend/なので、その親（プロジェクトルート）から相対パスを解決
                    from pathlib import Path
                    project_root = Path(settings.BASE_DIR).parent
                    credentials_path = str(project_root / credentials_path)
            
            if os.path.exists(credentials_path):
                # サービスアカウントキーから認証情報を読み込む
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                client = speech.SpeechClient(credentials=credentials)
            else:
                logger.warning(f'GCP認証情報ファイルが見つかりません: {credentials_path}')
                # デフォルト認証を使用（GCP環境やgcloud認証済みの場合）
                client = speech.SpeechClient()
        else:
            # デフォルト認証を使用（GCP環境やgcloud認証済みの場合）
            client = speech.SpeechClient()
        
        logger.info('GCP Speech-to-Text APIクライアントを初期化しました')
        return client
    except Exception as e:
        logger.error(f'GCP Speech-to-Text APIクライアントの初期化に失敗しました: {str(e)}')
        return None


def transcribe_audio(
    audio_data: bytes,
    language_code: str = 'ja-JP',
    sample_rate_hertz: int = 16000,
    encoding: speech.RecognitionConfig.AudioEncoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
) -> Dict[str, Any]:
    """
    音声データをテキストに変換
    
    Args:
        audio_data: 音声データ（バイト列）
        language_code: 言語コード（デフォルト: 'ja-JP'）
        sample_rate_hertz: サンプリングレート（デフォルト: 16000）
        encoding: 音声エンコーディング（デフォルト: LINEAR16）
    
    Returns:
        Dict[str, Any]: 変換結果
        {
            'text': str,  # 変換されたテキスト
            'confidence': float,  # 信頼度（0.0-1.0）
            'alternatives': list  # 代替候補（オプション）
        }
    
    Raises:
        Exception: 変換に失敗した場合
    """
    client = get_speech_client()
    if not client:
        raise Exception('GCP Speech-to-Text APIクライアントが初期化できませんでした')
    
    try:
        # 音声認識設定
        # GCP Speech-to-Text APIの推奨設定に基づく
        config_params = {
            'encoding': encoding,
            'language_code': language_code,
            'enable_automatic_punctuation': True,  # 自動句読点
            'enable_word_confidence': True,  # 単語レベルの信頼度
        }
        
        # サンプリングレートの設定
        # WEBM OPUS形式の場合は、サンプリングレートを指定しない（自動検出）
        # その他の形式の場合は、明示的にサンプリングレートを指定
        if encoding != speech.RecognitionConfig.AudioEncoding.WEBM_OPUS:
            config_params['sample_rate_hertz'] = sample_rate_hertz
        
        # 拡張モデルの使用（日本語の場合）
        # use_enhanced=Trueを使用する場合は、modelパラメータも指定する必要がある
        # 日本語の会話にはphone_callモデルが適している
        # ただし、use_enhancedとmodelの組み合わせは慎重に選択する必要がある
        if language_code.startswith('ja'):
            # phone_callモデルは電話音声向け、defaultモデルは汎用的
            # まずはdefaultモデルで試し、必要に応じてphone_callに変更
            config_params['model'] = 'default'  # 汎用モデルを使用
            # use_enhancedは日本語では利用可能だが、まずは標準モデルで試す
            # config_params['use_enhanced'] = True  # 必要に応じて有効化
        
        config = speech.RecognitionConfig(**config_params)
        
        # 音声データを設定
        audio = speech.RecognitionAudio(content=audio_data)
        
        # 音声認識を実行
        logger.info(f'音声認識を開始: language={language_code}, size={len(audio_data)} bytes, encoding={encoding}')
        
        try:
            response = client.recognize(config=config, audio=audio)
        except Exception as api_error:
            logger.error(f'GCP API呼び出しエラー: {str(api_error)}')
            # APIエラーの詳細をログに記録
            if hasattr(api_error, 'details'):
                logger.error(f'APIエラー詳細: {api_error.details}')
            raise Exception(f'音声認識API呼び出しに失敗しました: {str(api_error)}')
        
        # 結果を処理
        if not response.results:
            logger.warning(f'音声認識の結果が空でした。音声データのサイズ: {len(audio_data)} bytes, エンコーディング: {encoding}, サンプリングレート: {sample_rate_hertz}Hz')
            # 音声データの先頭部分をログに記録（デバッグ用）
            logger.debug(f'音声データの先頭16バイト: {audio_data[:16].hex()}')
            # より詳細なエラーメッセージを返す
            raise Exception('音声が認識できませんでした。音声が短すぎるか、無音の可能性があります。もう一度録音してください。')
        
        # 最初の結果を使用
        result = response.results[0]
        if not result.alternatives:
            logger.warning(f'音声認識の代替候補が空でした。音声データのサイズ: {len(audio_data)} bytes')
            raise Exception('音声が認識できませんでした。音声が短すぎるか、無音の可能性があります。もう一度録音してください。')
        
        alternative = result.alternatives[0]
        text = alternative.transcript
        confidence = alternative.confidence if hasattr(alternative, 'confidence') else 0.0
        
        # 代替候補を取得
        alternatives = []
        for alt in result.alternatives:
            alternatives.append({
                'text': alt.transcript,
                'confidence': alt.confidence if hasattr(alt, 'confidence') else 0.0
            })
        
        logger.info(f'音声認識完了: text="{text[:50]}...", confidence={confidence:.2f}')
        
        return {
            'text': text,
            'confidence': confidence,
            'alternatives': alternatives
        }
    
    except Exception as e:
        logger.error(f'音声認識エラー: {str(e)}')
        raise Exception(f'音声認識に失敗しました: {str(e)}')


def convert_webm_to_wav(audio_data: bytes) -> tuple[bytes, int]:
    """
    WEBM形式の音声データをWAV形式に変換
    
    Args:
        audio_data: WEBM形式の音声データ（バイト列）
    
    Returns:
        tuple[bytes, int]: (WAV形式の音声データ（バイト列）, サンプリングレート)
    
    Raises:
        Exception: 変換に失敗した場合
    """
    if not PYDUB_AVAILABLE:
        raise Exception('pydubライブラリがインストールされていません。音声変換にはpydubが必要です。')
    
    try:
        # 一時ファイルにWEBMデータを書き込む
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as webm_file:
            webm_file.write(audio_data)
            webm_file_path = webm_file.name
        
        try:
            # pydubでWEBMを読み込んでWAVに変換
            audio = AudioSegment.from_file(webm_file_path, format="webm")
            
            # サンプリングレートを取得（デフォルトは16000Hz）
            sample_rate = audio.frame_rate
            duration_ms = len(audio)
            duration_sec = duration_ms / 1000.0
            logger.info(f'元の音声情報: サンプリングレート={sample_rate}Hz, チャンネル数={audio.channels}, 長さ={duration_sec:.2f}秒 ({duration_ms}ms)')
            
            # 音声が短すぎる場合は警告
            if duration_sec < 0.5:
                logger.warning(f'音声が短すぎます: {duration_sec:.2f}秒。最低0.5秒以上推奨')
            elif duration_sec < 1.0:
                logger.info(f'音声の長さ: {duration_sec:.2f}秒（推奨: 1秒以上）')
            
            # サンプリングレートを16000Hzに変換（GCP Speech-to-Text APIの推奨値）
            if sample_rate != 16000:
                audio = audio.set_frame_rate(16000)
                sample_rate = 16000
                logger.info(f'サンプリングレートを16000Hzに変換しました')
            
            # モノラルに変換
            if audio.channels > 1:
                audio = audio.set_channels(1)
                logger.info('ステレオからモノラルに変換しました')
            
            # 音量を正規化（オプション）
            # 音声が小さすぎる場合は音量を上げる
            if audio.max_possible_amplitude > 0:
                max_dBFS = audio.max_dBFS
                logger.info(f'音声の最大音量: {max_dBFS:.1f}dBFS')
                if max_dBFS < -20:  # 音量が小さい場合
                    logger.info(f'音量が小さいため正規化します: {max_dBFS:.1f}dBFS')
                    audio = audio.normalize()
                    # 正規化後の音量を確認
                    normalized_dBFS = audio.max_dBFS
                    logger.info(f'正規化後の音量: {normalized_dBFS:.1f}dBFS')
                
                # 音量が非常に小さい場合（-60dBFS以下）は警告
                if max_dBFS < -60:
                    logger.warning(f'音声の音量が非常に小さいです: {max_dBFS:.1f}dBFS。マイクの音量設定を確認してください。')
            
            # WAV形式にエクスポート（16kHz、モノラル、16bit）
            wav_file_path = webm_file_path.replace('.webm', '.wav')
            audio.export(
                wav_file_path,
                format="wav",
                parameters=["-ar", str(sample_rate), "-ac", "1", "-sample_fmt", "s16"]
            )
            
            # WAVデータを読み込む
            with open(wav_file_path, 'rb') as wav_file:
                wav_data = wav_file.read()
            
            # 一時ファイルを削除
            os.unlink(webm_file_path)
            os.unlink(wav_file_path)
            
            logger.info(f'WEBMからWAVへの変換成功: {len(audio_data)} bytes -> {len(wav_data)} bytes, サンプリングレート: {sample_rate}Hz')
            return wav_data, sample_rate
        
        except Exception as e:
            # エラー時も一時ファイルを削除
            if os.path.exists(webm_file_path):
                os.unlink(webm_file_path)
            raise e
    
    except Exception as e:
        logger.error(f'WEBMからWAVへの変換エラー: {str(e)}')
        raise Exception(f'音声形式の変換に失敗しました: {str(e)}')


def detect_audio_encoding(audio_data: bytes) -> speech.RecognitionConfig.AudioEncoding:
    """
    音声データのエンコーディングを検出（簡易版）
    
    Args:
        audio_data: 音声データ（バイト列）
    
    Returns:
        AudioEncoding: 検出されたエンコーディング
    
    Raises:
        ValueError: 音声データが空または無効な場合
    """
    # 空のデータチェック
    if not audio_data:
        raise ValueError('音声データが空です')
    
    # 最小サイズチェック（4バイト未満の場合は判定不可）
    if len(audio_data) < 4:
        logger.warning(f'音声データが短すぎます（{len(audio_data)} bytes）。デフォルトのWEBM_OPUSとして扱います')
        return speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
    
    try:
        # WEBMファイルの場合はWEBM_OPUSを想定（MediaRecorder APIで録音された場合）
        if len(audio_data) >= 4 and audio_data[:4] == b'\x1a\x45\xdf\xa3':
            return speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
        # WEBM文字列チェック（最初の1024バイト内）
        if len(audio_data) >= 1024 and b'webm' in audio_data[:1024].lower():
            return speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
        elif len(audio_data) < 1024 and b'webm' in audio_data.lower():
            return speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
        
        # WAVファイルの場合はLINEAR16を想定
        if len(audio_data) >= 12 and audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
            return speech.RecognitionConfig.AudioEncoding.LINEAR16
        
        # MP3ファイルの場合はMP3を想定
        if len(audio_data) >= 3 and audio_data[:3] == b'ID3':
            return speech.RecognitionConfig.AudioEncoding.MP3
        if len(audio_data) >= 2 and audio_data[:2] == b'\xff\xfb':
            return speech.RecognitionConfig.AudioEncoding.MP3
        
        # FLACファイルの場合はFLACを想定
        if len(audio_data) >= 4 and audio_data[:4] == b'fLaC':
            return speech.RecognitionConfig.AudioEncoding.FLAC
        
        # デフォルトはWEBM_OPUS（MediaRecorder APIのデフォルト形式）
        logger.info(f'音声形式を検出できませんでした（サイズ: {len(audio_data)} bytes）。デフォルトのWEBM_OPUSとして扱います')
        return speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
    except Exception as e:
        logger.error(f'音声エンコーディング検出エラー: {str(e)}')
        # エラーが発生した場合はデフォルトのWEBM_OPUSを返す
        return speech.RecognitionConfig.AudioEncoding.WEBM_OPUS

