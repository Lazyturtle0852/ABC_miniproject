"""文字起こし（たいきが実装）"""

import os
import tempfile
from openai import OpenAI


def transcribe_video(video_data: bytes, client: OpenAI) -> tuple[str, str]:
    """
    録画データから音声を抽出して文字起こし

    【インターフェース】
    詳細は services/INTERFACE.md を参照してください。

    Args:
        video_data: WebM形式の動画データ（bytes）
        client: OpenAIクライアントインスタンス

    Returns:
        (transcription_text, status) のタプル
        - transcription_text: 文字起こし結果のテキスト（エラー時は空文字列）
        - status: "completed" または "error"

    Raises:
        Exception: 重大なエラーが発生した場合（UI層でキャッチする想定）
    """
    if not video_data or len(video_data) < 100:
        return "", "error"

    temp_input_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(video_data)
            temp_input_path = f.name

        with open(temp_input_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1", file=("audio.m4a", f), language="ja"
            )

        return response.text, "completed"

    except Exception as e:
        print(f"Whisperエラー詳細: {str(e)}")
        return "", "error"
    finally:
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
