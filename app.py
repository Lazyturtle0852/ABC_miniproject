"""
AI対話振り返りメディテーションシステム
メインUIアプリケーション
"""

import streamlit as st
import os
from typing import Optional
from dotenv import load_dotenv
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration
import av

from modules.video_processor import VideoProcessor
from modules.audio_processor import AudioProcessor
from modules.database import Database

# 環境変数の読み込み
load_dotenv()

# WebRTC設定
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)


class VideoProcessorCallback(VideoProcessorBase):
    """WebRTC映像処理コールバック"""

    def __init__(self):
        super().__init__()
        self.video_processor = VideoProcessor(frame_skip=30)

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        """フレームを受信して処理"""
        img = frame.to_ndarray(format="bgr24")

        # 映像処理
        processed_img, emotion = self.video_processor.process_frame(img)

        # セッション状態に感情を保存
        st.session_state.current_emotion = emotion

        return av.VideoFrame.from_ndarray(processed_img, format="bgr24")


def init_session_state():
    """セッション状態の初期化"""
    if "conversations" not in st.session_state:
        st.session_state.conversations = []

    if "current_user" not in st.session_state:
        st.session_state.current_user = "User A"

    if "current_emotion" not in st.session_state:
        st.session_state.current_emotion = None


def build_prompt(user_text: str, emotion: Optional[str]) -> str:
    """
    統合プロンプトを構築

    Args:
        user_text: ユーザーの発言
        emotion: 検出された感情

    Returns:
        構築されたプロンプト
    """
    system_prompt = """あなたは共感的なカウンセラーです。
ユーザーの言葉だけでなく、表情や声のトーンなどの非言語情報も考慮して、
ユーザー自身も気づいていない感情の機微を指摘し、受容的な対話を心がけてください。
"""

    emotion_info = (
        f"検出された表情: {emotion}" if emotion else "表情: 検出されていません"
    )

    user_prompt = f"""
{emotion_info}

ユーザーの発言: {user_text}

上記の情報を踏まえて、共感的に応答してください。
"""

    return system_prompt, user_prompt


def main():
    """メインアプリケーション"""
    st.set_page_config(
        page_title="AI対話振り返りメディテーションシステム",
        page_icon="🧘",
        layout="wide",
    )

    st.title("🧘 AI対話振り返りメディテーションシステム")
    st.markdown("---")

    # セッション状態の初期化
    init_session_state()

    # サイドバー
    with st.sidebar:
        st.header("設定")

        # ユーザー切り替え
        user_options = ["User A", "User B", "User C"]
        selected_user = st.selectbox(
            "ユーザー選択",
            user_options,
            index=user_options.index(st.session_state.current_user),
        )
        st.session_state.current_user = selected_user

        st.markdown("---")

        # 過去の感情グラフ
        st.header("感情の推移")
        db = Database()
        emotion_history = db.get_emotion_history(st.session_state.current_user)

        if emotion_history:
            # 感情を数値に変換（簡易版）
            emotion_map = {
                "happy": 1.0,
                "sad": -1.0,
                "angry": -0.5,
                "surprise": 0.5,
                "fear": -0.3,
                "disgust": -0.7,
                "neutral": 0.0,
            }

            emotion_values = [
                emotion_map.get(entry["emotion"].lower(), 0.0)
                for entry in emotion_history
            ]

            if emotion_values:
                st.line_chart(emotion_values)
        else:
            st.info("まだデータがありません")

    # メイン画面
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("📹 カメラ映像")

        # WebRTC映像ストリーム
        webrtc_ctx = webrtc_streamer(
            key="video",
            video_processor_factory=VideoProcessorCallback,
            rtc_configuration=RTC_CONFIGURATION,
            media_stream_constraints={"video": True, "audio": False},
        )

        if webrtc_ctx.state.playing:
            current_emotion = st.session_state.get("current_emotion", "Analyzing...")
            st.info(f"現在の感情: **{current_emotion}**")

    with col2:
        st.header("🎤 音声入力")

        # 音声入力
        audio_data = st.audio_input("録音を開始してください")

        if audio_data:
            with st.spinner("音声を処理中..."):
                # 音声処理
                audio_processor = AudioProcessor()

                # 文字起こし
                transcribed_text = audio_processor.transcribe_audio(audio_data.read())

                if transcribed_text:
                    st.success("音声認識完了")
                    st.write(f"**認識結果:** {transcribed_text}")

                    # トーン分析（オプション・後回し）
                    # tone_info = audio_processor.analyze_tone(audio_data.read())

                    # 現在の感情を取得
                    current_emotion = st.session_state.get("current_emotion")

                    # プロンプト構築
                    system_prompt, user_prompt = build_prompt(
                        transcribed_text, current_emotion
                    )

                    # ChatGPT API呼び出し
                    with st.spinner("AIが応答を生成中..."):
                        try:
                            from openai import OpenAI

                            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                            response = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt},
                                ],
                                temperature=0.7,
                            )

                            ai_response = response.choices[0].message.content

                            # 会話履歴に追加
                            st.session_state.conversations.append(
                                {
                                    "user": transcribed_text,
                                    "emotion": current_emotion,
                                    "ai": ai_response,
                                }
                            )

                            # データベースに保存
                            db = Database()
                            db.save_log(
                                user_id=st.session_state.current_user,
                                user_voice_text=transcribed_text,
                                detected_emotion=current_emotion,
                                ai_response=ai_response,
                            )

                            st.success("応答を生成しました")
                            st.write(f"**AI:** {ai_response}")

                        except Exception as e:
                            st.error(f"API呼び出しエラー: {e}")
                            st.info("APIキーが正しく設定されているか確認してください")

                else:
                    st.error("音声認識に失敗しました")

    # チャットログ表示
    st.markdown("---")
    st.header("💬 対話履歴")

    if st.session_state.conversations:
        for i, conv in enumerate(reversed(st.session_state.conversations)):
            with st.expander(f"対話 {len(st.session_state.conversations) - i}"):
                st.write(f"**感情:** {conv.get('emotion', 'N/A')}")
                st.write(f"**あなた:** {conv['user']}")
                st.write(f"**AI:** {conv['ai']}")
    else:
        st.info("まだ対話がありません。音声を録音して対話を開始してください。")


if __name__ == "__main__":
    main()
