"""文字起こし（たいきが実装）"""

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

    TODO: C担当が実装してください
    """
    # ========================================
    # 仮実装: ダミーデータを返す
    # ========================================
    # TODO: 以下の実装を削除し、実際のWhisper API呼び出しを実装してください

    # 仮の戻り値
    return (
        "（仮）文字起こし結果テキスト：録画データから音声を抽出して文字起こしを行いました。",
        "completed",
    )

    # ========================================
    # 実装時の注意事項:
    # ========================================
    # 1. 一時ファイルにvideo_dataを保存
    # 2. Whisper APIに送信（client.audio.transcriptions.create()）
    # 3. 一時ファイルを削除（必ずfinallyで削除すること）
    # 4. エラー時は("", "error")を返す
    # 5. 重大なエラーはExceptionをraiseする

    # 実装例（参考）:
    # import os
    # temp_video_file = "temp_recording.webm"
    # try:
    #     with open(temp_video_file, "wb") as f:
    #         f.write(video_data)
    #     with open(temp_video_file, "rb") as f:
    #         response = client.audio.transcriptions.create(
    #             model="whisper-1", file=f, language="ja"
    #         )
    #     return response.text, "completed"
    # except Exception as e:
    #     return "", "error"
    # finally:
    #     if os.path.exists(temp_video_file):
    #         os.remove(temp_video_file)
