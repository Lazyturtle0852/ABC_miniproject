"""
音声処理モジュール
Whisper APIによる音声認識とlibrosaによるトーン分析
"""

import os
import tempfile
from typing import Optional, Dict, Tuple
import openai
from openai import OpenAI

# librosaはオプション（トーン分析用、後回し可）
try:
    import librosa
    import numpy as np

    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    librosa = None
    np = None


class AudioProcessor:
    """音声処理クラス"""

    def __init__(self, api_key: Optional[str] = None):
        """
        音声処理の初期化

        Args:
            api_key: OpenAI APIキー（Noneの場合は環境変数から取得）
        """
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    def transcribe_audio(
        self, audio_data: bytes, filename: str = "audio.wav"
    ) -> Optional[str]:
        """
        Whisper APIを使用して音声を文字起こし

        Args:
            audio_data: 音声データ（バイト列）
            filename: 一時ファイル名

        Returns:
            文字起こし結果（エラー時はNone）
        """
        temp_file = None
        try:
            # 一時ファイルに保存
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".wav", mode="wb"
            ) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            # Whisper APIで文字起こし
            with open(temp_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1", file=audio_file, language="ja"
                )

            return transcript.text

        except Exception as e:
            print(f"音声認識エラー: {e}")
            return None

        finally:
            # 一時ファイルを削除（クリーンアップ）
            if temp_file and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    print(f"一時ファイル削除エラー: {e}")

    def analyze_tone(self, audio_data: bytes) -> Optional[Dict[str, float]]:
        """
        librosaを使用して音声のトーンを分析（軽量処理）

        Args:
            audio_data: 音声データ（バイト列）

        Returns:
            トーン分析結果（rms: 音量, tempo: 話速）エラー時はNone
        """
        # librosaがインストールされていない場合はNoneを返す
        if not LIBROSA_AVAILABLE:
            return None

        temp_file = None
        try:
            # 一時ファイルに保存
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".wav", mode="wb"
            ) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            # librosaで音声を読み込み
            y, sr = librosa.load(temp_file_path, sr=None)

            # RMS（音量）の計算
            rms = librosa.feature.rms(y=y)[0]
            rms_mean = float(np.mean(rms))

            # Tempo（話速）の計算
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            tempo_value = float(tempo)

            return {"rms": rms_mean, "tempo": tempo_value}

        except Exception as e:
            print(f"トーン分析エラー: {e}")
            return None

        finally:
            # 一時ファイルを削除（クリーンアップ）
            if temp_file and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    print(f"一時ファイル削除エラー: {e}")
