"""共通ユーティリティ関数"""
from datetime import datetime
import os
import streamlit as st
from openai import OpenAI


def init_session_state():
    """セッション状態の初期化"""
    if "emotion_coords" not in st.session_state:
        st.session_state["emotion_coords"] = (0.0, 0.0)  # (x, y) tuple

    if "is_recording" not in st.session_state:
        st.session_state["is_recording"] = False

    if "recording_started_at" not in st.session_state:
        st.session_state["recording_started_at"] = None

    # "収録データ"の格納先（MVPなので session_state に保持）
    if "video_buffer" not in st.session_state:
        st.session_state["video_buffer"] = None  # bytes など想定（今はプレースホルダ可）

    if "audio_buffer" not in st.session_state:
        st.session_state["audio_buffer"] = None  # bytes など想定

    # カメラ/音声の最新入力（UIから得た生データ）
    if "captured_frame" not in st.session_state:
        st.session_state["captured_frame"] = None  # UploadedFile（静止画）
    if "captured_audio" not in st.session_state:
        st.session_state["captured_audio"] = None  # UploadedFile（音声）

    # 録画データ
    if "recorded_video_data" not in st.session_state:
        st.session_state["recorded_video_data"] = None  # 録画した動画データ（bytes）
    if "recording_trigger" not in st.session_state:
        st.session_state["recording_trigger"] = 0  # 録画開始/停止のトリガー

    # 音声認識結果
    if "transcription_result" not in st.session_state:
        st.session_state["transcription_result"] = None  # 文字起こし結果のテキスト
    if "transcription_status" not in st.session_state:
        st.session_state["transcription_status"] = "idle"  # 処理状態（"idle", "processing", "completed", "error")

    # 対話関連
    if "conversation_history" not in st.session_state:
        st.session_state["conversation_history"] = []  # 対話履歴
    if "ai_response" not in st.session_state:
        st.session_state["ai_response"] = None  # AI応答


def get_openai_client():
    """OpenAIクライアントを取得"""
    try:
        return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    except (KeyError, AttributeError):
        return None
