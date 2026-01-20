"""共通ユーティリティ関数

セッション状態の初期化、対話履歴の管理、OpenAIクライアントの取得を提供します。
"""

import streamlit as st
from openai import OpenAI
from services.database import (
    is_db_available,
    init_database,
    load_conversation_history_from_db,
    save_conversation_to_db,
)


def init_session_state():
    """セッション状態の初期化"""
    if "emotion_coords" not in st.session_state:
        st.session_state["emotion_coords"] = (0.0, 0.0)  # (x, y) tuple

    if "is_recording" not in st.session_state:
        st.session_state["is_recording"] = False

    if "recording_started_at" not in st.session_state:
        st.session_state["recording_started_at"] = None

    # 録画データ
    if "recorded_video_data" not in st.session_state:
        st.session_state["recorded_video_data"] = None  # 録画した動画データ（bytes）
    if "analysis_trigger" not in st.session_state:
        st.session_state["analysis_trigger"] = False  # 分析開始のトリガー
    if "recording_path" not in st.session_state:
        st.session_state["recording_path"] = None  # WebRTC録画ファイル
    if "was_playing" not in st.session_state:
        st.session_state["was_playing"] = False  # 直前の録画状態

    # 音声認識結果
    if "transcription_result" not in st.session_state:
        st.session_state["transcription_result"] = None  # 文字起こし結果のテキスト
    if "transcription_status" not in st.session_state:
        st.session_state["transcription_status"] = (
            "idle"  # 処理状態（"idle", "processing", "completed", "error")
        )

    # 表情認識結果
    if "face_emotion_result" not in st.session_state:
        st.session_state["face_emotion_result"] = None  # 表情認識結果（dict | None）
    if "face_emotion_status" not in st.session_state:
        st.session_state["face_emotion_status"] = (
            "idle"  # 処理状態（"idle", "processing", "completed", "error")
        )

    # 対話関連
    if "conversation_history" not in st.session_state:
        # データベースから履歴を読み込む（利用可能な場合）
        st.session_state["conversation_history"] = load_conversation_history()
    if "ai_response" not in st.session_state:
        st.session_state["ai_response"] = None  # AI応答

    # データベースの初期化（初回のみ、利用可能な場合）
    if "db_initialized" not in st.session_state:
        if is_db_available():
            init_database()
        st.session_state["db_initialized"] = True


def load_conversation_history():
    """対話履歴を読み込む（データベースから、または空リスト）"""
    if is_db_available():
        try:
            history = load_conversation_history_from_db()
            return history
        except Exception as e:
            # エラー時は空リストを返す（メモリのみモード）
            return []
    return []


def save_conversation(conversation_data):
    """対話履歴を保存（session_stateには常に保存、DBは利用可能な場合のみ）"""
    # session_stateには常に保存
    if "conversation_history" not in st.session_state:
        st.session_state["conversation_history"] = []
    st.session_state["conversation_history"].append(conversation_data)

    # データベースが利用可能な場合のみ保存
    if is_db_available():
        try:
            save_conversation_to_db(conversation_data)
        except Exception:
            # エラー時はスキップ（メモリのみモードで継続）
            pass


def get_openai_client():
    """OpenAIクライアントを取得"""
    try:
        return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    except (KeyError, AttributeError):
        return None
