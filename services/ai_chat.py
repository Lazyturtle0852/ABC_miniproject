"""AI対話サービス（やなこうが実装）- プロンプト構築 + ChatGPT API"""

from openai import OpenAI


def generate_ai_response(
    transcription_text: str,
    emotion_params: dict | tuple[float, float],
    face_emotion: dict | None = None,
    client: OpenAI | None = None,
) -> tuple[str, str]:
    """
    AI応答を生成（プロンプト構築 + ChatGPT API呼び出し）

    【インターフェース】
    詳細は services/INTERFACE.md を参照してください。

    Args:
        transcription_text: 文字起こし結果のテキスト（空文字列不可）
        emotion_params: 感情パラメータ辞書またはタプル（後方互換性のため）
            - 辞書形式: {"pleasure": float, "arousal": float, "confidence": float, "energy": float, "productivity": float, "redo_today": float}
            - タプル形式: (pleasure, arousal) - 後方互換性のため
        face_emotion: 顔感情分析結果（オプション、将来実装用、現在はNone）
        client: OpenAIクライアントインスタンス（Noneの場合は内部で取得を試みる）

    Returns:
        (ai_response, status) のタプル
        - ai_response: AI応答テキスト（エラー時は空文字列）
        - status: "completed" または "error"

    Raises:
        Exception: 重大なエラーが発生した場合（UI層でキャッチする想定）
    """
    if not transcription_text:
        return "", "error"

    if client is None:
        return "", "error"

    # 後方互換性: タプル形式の場合は辞書に変換
    if isinstance(emotion_params, (tuple, list)):
        if len(emotion_params) >= 2:
            emotion_dict = {
                "pleasure": float(emotion_params[0]),
                "arousal": float(emotion_params[1]),
                "confidence": 0.0,
                "energy": 0.0,
                "productivity": 0.0,
                "redo_today": 0.0,
            }
        else:
            emotion_dict = {
                "pleasure": 0.0,
                "arousal": 0.0,
                "confidence": 0.0,
                "energy": 0.0,
                "productivity": 0.0,
                "redo_today": 0.0,
            }
    elif isinstance(emotion_params, dict):
        emotion_dict = {
            "pleasure": float(emotion_params.get("pleasure", 0.0)),
            "arousal": float(emotion_params.get("arousal", 0.0)),
            "confidence": float(emotion_params.get("confidence", 0.0)),
            "energy": float(emotion_params.get("energy", 0.0)),
            "productivity": float(emotion_params.get("productivity", 0.0)),
            "redo_today": float(emotion_params.get("redo_today", 0.0)),
        }
    else:
        emotion_dict = {
            "pleasure": 0.0,
            "arousal": 0.0,
            "confidence": 0.0,
            "energy": 0.0,
            "productivity": 0.0,
            "redo_today": 0.0,
        }

    def get_emotion_description(value: float, positive_labels: tuple[str, str], negative_labels: tuple[str, str]) -> str:
        """感情値から説明文を生成"""
        if value > 0.5:
            return f"非常に{positive_labels[0]}"
        elif value > 0:
            return f"やや{positive_labels[1]}"
        elif value > -0.5:
            return f"やや{negative_labels[1]}"
        else:
            return f"非常に{negative_labels[0]}"

    pleasure_desc = get_emotion_description(emotion_dict["pleasure"], ("快", "快"), ("不快", "不快"))
    arousal_desc = get_emotion_description(emotion_dict["arousal"], ("覚醒", "覚醒"), ("落ち着き", "落ち着き"))
    confidence_desc = get_emotion_description(emotion_dict["confidence"], ("自信", "自信"), ("不安", "不安"))
    energy_desc = get_emotion_description(emotion_dict["energy"], ("エネルギー", "エネルギー"), ("疲労", "疲労"))
    productivity_desc = get_emotion_description(emotion_dict["productivity"], ("高", "高"), ("低", "低"))
    redo_desc = get_emotion_description(emotion_dict["redo_today"], ("やり直したくない", "やり直したくない"), ("やり直したい", "やり直したい"))

    system_prompt = """あなたは就寝前のメンタルヘルスを整えるAIコーチングシステムです。小難しく医療行為や診断を行う医師ではなく、ユーザーと生活を共にしているカウンセラーであると考えてください。
あなたの目的は、ユーザーの感情状態（快/不快軸・覚醒/非覚醒（落ち着き）軸・自信/不安・エネルギー/疲労・生産性高い/生産性低い・今日をやり直したいか/今日をやり直したくないか）や表情データ、発話内容をもとにユーザーが自身の感情や状況を整理しやすくなる対話を優しく寄り添いながら行うことです。

あなたの役割
1. 絶対にユーザーを否定せず、受け止め寄り添う。
2. 感情の言語化のサポートを行う。
3. AI的な返答ではなく、心に寄り添うカウンセラーとしての返答を行う。

感情プロットの使い方
1. 快よりの時：気持ちを落とさせないよう少しテンションを高めにする。
2. 不快よりの時：共感を強めて、テンション抑え目にする。
3. 覚醒よりの時：文章量を少なくし、ユーザーを落ち着かせるよう心がける。
4. 非覚醒（落ち着き）よりの時：落ち着いたトーンで思考を促す。
5. エネルギーよりの時：明るめなトーンで翌日以降の小さな挑戦などを提案（提案しなくても良い、ケースバイケースで）
6. 疲労よりの時：落ち着いたトーンで休むことを正当化した文章を少し入れ込む。
7. 生産性が高い時：達成感を持たせる返答をする。
8. 生産性が低い時：できなかったことを否定せず、休むよう促す。
9. 自信よりの時：自信を過度に盛り上げないように、落ち着いたトーンで話す。
10. 不安よりの時：不安である状態は自然であると肯定し、共感を強める。
11. 今日をやり直したくないよりの時：少しテンションを高めに、次の日に期待を持たせるような話し方で。
12. 今日をやり直したいよりの時：今日うまく行ったことに焦点を当てる。落ち着いた包み込むようなトーンで対話。"""

    user_prompt = f"""ユーザーが話した内容：
「{transcription_text}」

ユーザーの現在の感情状態：
- 快/不快軸: {emotion_dict['pleasure']:.2f} ({pleasure_desc})
- 覚醒/落ち着き軸: {emotion_dict['arousal']:.2f} ({arousal_desc})
- 自信/不安軸: {emotion_dict['confidence']:.2f} ({confidence_desc})
- エネルギー/疲労軸: {emotion_dict['energy']:.2f} ({energy_desc})
- 生産性: {emotion_dict['productivity']:.2f} ({productivity_desc})
- 今日をやり直したいか: {emotion_dict['redo_today']:.2f} ({redo_desc})"""

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
