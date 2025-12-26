"""表情認識サービス（GPT-4o Vision使用）- エマが実装"""

import base64
import cv2
import numpy as np
from openai import OpenAI
from typing import tuple
import os
import tempfile


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
    # TODO: 担当1が実装してください
    # 実装時の注意事項:
    # 1. 一時ファイルにvideo_dataを保存
    # 2. OpenCVでWebMを読み込み
    # 3. 指定間隔（interval_seconds）ごとにフレームを抽出
    # 4. 各フレームをJPEG形式にエンコードしてbytesのリストとして返す
    # 5. 一時ファイルを削除

    # 仮実装: ダミーデータを返す
    return []


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
    # TODO: 担当1が実装してください
    # 実装時の注意事項:
    # 1. フレームをbase64エンコード
    # 2. GPT-4o Vision APIに送信
    # 3. プロンプト: "この画像の人物の表情から感情を分析してください。"
    #    感情（happy, sad, angry, surprised, neutral など）と信頼度（0.0-1.0）を
    #    JSON形式で返してください。
    # 4. レスポンスから感情と信頼度を抽出
    # 5. エラー時は{"emotion": "neutral", "confidence": 0.0, "description": ""}を返す

    # 仮実装: ダミーデータを返す
    return {
        "emotion": "neutral",
        "confidence": 0.0,
        "description": "（仮）ダミーデータ",
    }


def analyze_face_emotion(
    video_data: bytes,
    client: OpenAI,
    interval_seconds: float = 5.0,
) -> tuple[dict | None, str]:
    """
    WebM録画データから表情認識を実行（GPT-4o Vision使用）

    Args:
        video_data: WebM形式の動画データ（bytes）
        client: OpenAIクライアント
        interval_seconds: フレーム抽出間隔（秒、デフォルト: 5.0）

    Returns:
        (face_emotion_result, status) のタプル
        - face_emotion_result: {
            "emotions": list[str],  # 各フレームの感情リスト
            "dominant_emotion": str,  # 最も多い感情
            "confidence": float,  # 平均信頼度
            "frame_count": int  # 分析したフレーム数
          } または None
        - status: "completed" または "error"

    Raises:
        Exception: 重大なエラーが発生した場合

    TODO: 担当1が実装してください
    """
    # ========================================
    # 仮実装: ダミーデータを返す
    # ========================================
    # TODO: 以下の実装を削除し、実際の表情認識処理を実装してください

    # 仮の戻り値
    return (
        {
            "emotions": ["happy", "neutral", "happy"],
            "dominant_emotion": "happy",
            "confidence": 0.75,
            "frame_count": 3,
        },
        "completed",
    )

    # ========================================
    # 実装時の注意事項:
    # ========================================
    # 1. extract_frames_from_webm()でフレーム抽出
    # 2. 各フレームをanalyze_emotion_with_gpt4o_vision()で分析
    # 3. 結果を集約（最も多い感情をdominant_emotionとして決定）
    # 4. 平均信頼度を計算
    # 5. エラー時は(None, "error")を返す
    # 6. 重大なエラーはExceptionをraiseする

    # 実装例（参考）:
    # try:
    #     frames = extract_frames_from_webm(video_data, interval_seconds)
    #     if not frames:
    #         return None, "error"
    #
    #     emotions = []
    #     confidences = []
    #     for frame in frames:
    #         result = analyze_emotion_with_gpt4o_vision(frame, client)
    #         emotions.append(result["emotion"])
    #         confidences.append(result["confidence"])
    #
    #     # 最も多い感情を決定
    #     from collections import Counter
    #     emotion_counts = Counter(emotions)
    #     dominant_emotion = emotion_counts.most_common(1)[0][0]
    #
    #     return {
    #         "emotions": emotions,
    #         "dominant_emotion": dominant_emotion,
    #         "confidence": sum(confidences) / len(confidences) if confidences else 0.0,
    #         "frame_count": len(frames),
    #     }, "completed"
    # except Exception as e:
    #     return None, "error"
