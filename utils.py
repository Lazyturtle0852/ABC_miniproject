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
    # ユーザー名が設定されている場合、データベースから履歴を再読み込み
    if "username" in st.session_state and st.session_state["username"]:
        current_username = st.session_state["username"]
        # 最後に読み込んだユーザー名を記録
        last_loaded_username = st.session_state.get("last_loaded_username")
        
        # 履歴が存在しない、またはユーザー名が変更された場合に再読み込み
        if ("conversation_history" not in st.session_state or 
            last_loaded_username != current_username):
            # データベースから履歴を読み込む（利用可能な場合）
            st.session_state["conversation_history"] = load_conversation_history(current_username)
            st.session_state["last_loaded_username"] = current_username
    elif "conversation_history" not in st.session_state:
        # ユーザー名が設定されていない場合は空リスト
        st.session_state["conversation_history"] = []
    if "ai_response" not in st.session_state:
        st.session_state["ai_response"] = None  # AI応答

    # データベースの初期化（初回のみ、利用可能な場合）
    if "db_initialized" not in st.session_state:
        if is_db_available():
            init_database()
        st.session_state["db_initialized"] = True


def load_conversation_history(username: str = None):
    """対話履歴を読み込む（データベースから、または空リスト）"""
    if username and is_db_available():
        try:
            history = load_conversation_history_from_db(username)
            return history
        except Exception as e:
            # エラー時は空リストを返す（メモリのみモード）
            return []
    return []


def save_conversation(conversation_data, username: str = None):
    """対話履歴を保存（session_stateには常に保存、DBは利用可能な場合のみ）"""
    # session_stateには常に保存
    if "conversation_history" not in st.session_state:
        st.session_state["conversation_history"] = []
    st.session_state["conversation_history"].append(conversation_data)

    # データベースが利用可能な場合のみ保存
    if username and is_db_available():
        try:
            success = save_conversation_to_db(conversation_data, username)
            if not success:
                import logging
                logging.warning(f"データベースへの保存に失敗しました（ユーザー名: {username}）")
        except Exception as e:
            # エラー時はスキップ（メモリのみモードで継続）
            import logging
            logging.warning(f"データベース保存エラー（ユーザー名: {username}）: {e}")


def get_openai_client():
    """OpenAIクライアントを取得"""
    try:
        return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    except (KeyError, AttributeError):
        return None


def get_ice_servers():
    """TwilioからICEサーバー情報を取得（設定されていない場合はSTUNのみ）"""
    try:
        if "TWILIO_ACCOUNT_SID" in st.secrets and "TWILIO_AUTH_TOKEN" in st.secrets:
            from twilio.rest import Client

            client = Client(
                st.secrets["TWILIO_ACCOUNT_SID"], st.secrets["TWILIO_AUTH_TOKEN"]
            )
            token = client.tokens.create()
            return token.ice_servers
    except Exception:
        pass

    # フォールバック: STUNサーバーのみ
    return [{"urls": ["stun:stun.l.google.com:19302"]}]
