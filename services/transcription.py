"""文字起こし（たいきが実装）"""

import os
import tempfile
import traceback
from openai import OpenAI


def transcribe_video(video_data: bytes, client: OpenAI) -> tuple[str, str, str]:
    """
    録画データから音声を抽出して文字起こし

    【インターフェース】
    詳細は services/INTERFACE.md を参照してください。

    Args:
        video_data: WebM形式の動画データ（bytes）
        client: OpenAIクライアントインスタンス

    Returns:
        (transcription_text, status, error_message) のタプル
        - transcription_text: 文字起こし結果のテキスト（エラー時は空文字列）
        - status: "completed" または "error"
        - error_message: エラーメッセージ（エラー時）

    Raises:
        Exception: 重大なエラーが発生した場合（UI層でキャッチする想定）
    """
    if not video_data or len(video_data) < 100:
        return "", "error", "動画データが無効です（サイズが小さすぎます）"

    temp_input_path = None
    try:
        # 一時ファイルを作成（拡張子を.webmに指定）
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
            f.write(video_data)
            temp_input_path = f.name

        with open(temp_input_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1", file=("audio.webm", f), language="ja"
            )

        return response.text, "completed", ""

    except Exception as e:
        error_msg = f"Whisper APIエラー: {str(e)}\n詳細: {traceback.format_exc()}"
        print(error_msg)
        return "", "error", error_msg
    finally:
        if temp_input_path and os.path.exists(temp_input_path):
            try:
                os.remove(temp_input_path)
            except Exception:
                pass
