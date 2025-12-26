"""AI対話サービス（B担当が実装）- プロンプト構築 + ChatGPT API"""

from openai import OpenAI


def generate_ai_response(
    transcription_text: str,
    emotion_coords: tuple[float, float],
    face_emotion: dict | None = None,
    client: OpenAI | None = None,
) -> tuple[str, str]:
    """
    AI応答を生成（プロンプト構築 + ChatGPT API呼び出し）

    【インターフェース】
    詳細は services/INTERFACE.md を参照してください。

    Args:
        transcription_text: 文字起こし結果のテキスト（空文字列不可）
        emotion_coords: 感情座標タプル (x, y)。x, y は -1.0 ～ 1.0
        face_emotion: 顔感情分析結果（オプション、将来実装用、現在はNone）
        client: OpenAIクライアントインスタンス（Noneの場合は内部で取得を試みる）

    Returns:
        (ai_response, status) のタプル
        - ai_response: AI応答テキスト（エラー時は空文字列）
        - status: "completed" または "error"

    Raises:
        Exception: 重大なエラーが発生した場合（UI層でキャッチする想定）

    TODO: B担当が実装してください
    """
    # ========================================
    # 仮実装: ダミーデータを返す
    # ========================================
    # TODO: 以下の実装を削除し、実際のプロンプト構築とChatGPT API呼び出しを実装してください

    # 仮の戻り値
    return (
        "（仮）AI応答テキスト：あなたの感情を理解しました。"
        f"文字起こし結果: {transcription_text[:20]}... "
        f"感情座標: {emotion_coords}",
        "completed",
    )

    # ========================================
    # 実装時の注意事項:
    # ========================================
    # 1. transcription_textが空でないかチェック
    # 2. emotion_coordsから感情の説明を生成
    # 3. プロンプトを構築（system_prompt, user_prompt）
    # 4. ChatGPT APIを呼び出し（client.chat.completions.create()）
    # 5. エラー時は("", "error")を返す
    # 6. 重大なエラーはExceptionをraiseする

    # 実装例（参考）:
    # if not transcription_text:
    #     return "", "error"
    #
    # x, y = emotion_coords
    # # 感情の説明を生成...
    # system_prompt = "..."
    # user_prompt = f"..."
    #
    # try:
    #     response = client.chat.completions.create(
    #         model="gpt-4o-mini",
    #         messages=[
    #             {"role": "system", "content": system_prompt},
    #             {"role": "user", "content": user_prompt},
    #         ],
    #         temperature=0.7,
    #     )
    #     return response.choices[0].message.content, "completed"
    # except Exception as e:
    #     return "", "error"
