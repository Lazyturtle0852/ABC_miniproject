"""AI対話サービス（やなこうが実装）- プロンプト構築 + ChatGPT API"""

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
    if not transcription_text:
        return "", "error"

    if client is None:
        return "", "error"

    x, y = emotion_coords

    # 感情の説明を生成
    if x > 0.5:
        pleasure_desc = "非常に快"
    elif x > 0:
        pleasure_desc = "やや快"
    elif x > -0.5:
        pleasure_desc = "やや不快"
    else:
        pleasure_desc = "非常に不快"

    if y > 0.5:
        arousal_desc = "非常に覚醒"
    elif y > 0:
        arousal_desc = "やや覚醒"
    elif y > -0.5:
        arousal_desc = "やや落ち着き"
    else:
        arousal_desc = "非常に落ち着き"

    system_prompt = """あなたはメンタルヘルスケアの専門家です。
ユーザーの感情状態を理解し、共感的でサポート的な対話を行ってください。
ユーザーの感情に寄り添いながら、適切なアドバイスや質問を提供してください。"""

    user_prompt = f"""ユーザーが話した内容：
「{transcription_text}」

ユーザーの現在の感情状態：
- 快/不快軸（X軸）: {x:.2f} ({pleasure_desc})
- 覚醒/落ち着き軸（Y軸）: {y:.2f} ({arousal_desc})"""

    # 表情データがある場合は追加
    if face_emotion:
        dominant = face_emotion.get("dominant_emotion", "unknown")
        confidence = face_emotion.get("confidence", 0.0)
        user_prompt += f"\n- 検出された表情: {dominant} (信頼度: {confidence:.2f})"

    user_prompt += (
        "\n\nこの感情状態と話した内容を踏まえて、適切な応答を生成してください。"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content, "completed"
    except Exception as e:
        print(f"ChatGPT APIエラー詳細: {str(e)}")
        return "", "error"
