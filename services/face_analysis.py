"""表情認識サービス（GPT-4o Vision使用）- エマが実装"""

import base64
import cv2
import json
from openai import OpenAI
import os
import tempfile
from collections import Counter


def extract_frames_from_webm(
    video_data: bytes,
    interval_seconds: float = 5.0,
) -> list[bytes]:
    """
    WebMから指定間隔でフレームを抽出

    Args:
        video_data: WebM形式の動画データ（bytes）
        interval_seconds: フレーム抽出間隔（秒）

    Returns:
        抽出したフレームのリスト（各フレームはJPEG形式のbytes）
    """
    temp_video_path = None
    cap = None
    try:
        if not video_data or len(video_data) < 100:
            return []

        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
            f.write(video_data)
            temp_video_path = f.name

        cap = cv2.VideoCapture(temp_video_path)
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = 30.0
        interval_frames = max(1, int(round(fps * max(0.1, interval_seconds))))

        frames: list[bytes] = []
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % interval_frames == 0:
                ok, buffer = cv2.imencode(".jpg", frame)
                if ok:
                    frames.append(buffer.tobytes())
            frame_idx += 1

        return frames
    finally:
        if cap is not None:
            cap.release()
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)


def analyze_emotion_with_gpt4o_vision(
    frame_image: bytes,
    client: OpenAI,
) -> dict:
    """
    1フレームの画像をGPT-4o Visionで分析

    Args:
        frame_image: JPEG形式の画像データ（bytes）
        client: OpenAIクライアント

    Returns:
        {"emotion": str, "confidence": float, "description": str}
    """
    try:
        if not frame_image:
            return {"emotion": "neutral", "confidence": 0.0, "description": ""}

        base64_image = base64.b64encode(frame_image).decode("utf-8")
        prompt = (
            "この画像の人物の表情から感情を分析してください。"
            "次のJSONだけを返してください。"
            '{"emotion":"happy|sad|angry|surprised|neutral|other","confidence":0.0,"description":""}'
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            temperature=0.2,
        )

        content = response.choices[0].message.content or ""
        try:
            data = json.loads(content)
            return {
                "emotion": str(data.get("emotion", "neutral")),
                "confidence": float(data.get("confidence", 0.0)),
                "description": str(data.get("description", "")),
            }
        except json.JSONDecodeError:
            return {"emotion": "neutral", "confidence": 0.0, "description": content}
    except Exception:
        return {"emotion": "neutral", "confidence": 0.0, "description": ""}


def analyze_face_emotion(
    video_data: bytes,
    client: OpenAI,
    interval_seconds: float = 5.0,
) -> tuple[dict | None, str, str]:
    """
    WebM録画データから表情認識を実行（GPT-4o Vision使用）

    Args:
        video_data: WebM形式の動画データ（bytes）
        client: OpenAIクライアント
        interval_seconds: フレーム抽出間隔（秒、デフォルト: 5.0）

    Returns:
        (face_emotion_result, status, error_message) のタプル
        - face_emotion_result: {
            "emotions": list[str],  # 各フレームの感情リスト
            "dominant_emotion": str,  # 最も多い感情
            "confidence": float,  # 平均信頼度
            "frame_count": int  # 分析したフレーム数
          } または None
        - status: "completed" または "error"
        - error_message: エラーメッセージ（エラー時）

    Raises:
        Exception: 重大なエラーが発生した場合
    """
    import traceback

    try:
        frames = extract_frames_from_webm(video_data, interval_seconds)
        if not frames:
            return (
                None,
                "error",
                "フレームの抽出に失敗しました（動画が空か無効な形式です）",
            )

        emotions: list[str] = []
        confidences: list[float] = []
        for frame in frames:
            result = analyze_emotion_with_gpt4o_vision(frame, client)
            emotions.append(result.get("emotion", "neutral"))
            confidences.append(float(result.get("confidence", 0.0)))

        emotion_counts = Counter(emotions)
        dominant_emotion = emotion_counts.most_common(1)[0][0]

        return (
            {
                "emotions": emotions,
                "dominant_emotion": dominant_emotion,
                "confidence": sum(confidences) / len(confidences)
                if confidences
                else 0.0,
                "frame_count": len(frames),
            },
            "completed",
            "",
        )
    except Exception as e:
        error_msg = f"表情認識エラー: {str(e)}\n詳細: {traceback.format_exc()}"
        print(error_msg)
        return None, "error", error_msg
