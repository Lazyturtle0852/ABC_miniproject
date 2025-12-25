"""ページ3: 対話・結果"""

import streamlit as st
from datetime import datetime
from utils import init_session_state, get_openai_client

st.set_page_config(page_title="対話結果", layout="wide")

# セッション状態の初期化
init_session_state()

# OpenAIクライアントの取得
client = get_openai_client()

st.title("💬 対話・結果")

st.markdown("文字起こし結果とAI応答を確認できます。")


# プロンプト構築関数
def build_conversation_prompt(transcription_text, emotion_coords):
    """文字起こし結果と感情データからプロンプトを構築"""
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
- 覚醒/落ち着き軸（Y軸）: {y:.2f} ({arousal_desc})

この感情状態と話した内容を踏まえて、適切な応答を生成してください。"""

    return system_prompt, user_prompt


# 文字起こし結果の表示
if st.session_state["transcription_result"]:
    st.markdown("---")
    st.subheader("📝 文字起こし結果")
    if st.session_state["transcription_status"] == "completed":
        st.success(st.session_state["transcription_result"])

        # 自動的にAI応答を生成（まだ生成されていない場合）
        if (
            client is not None
            and "OPENAI_API_KEY" in st.secrets
            and st.session_state["ai_response"] is None
        ):
            with st.spinner("AI応答を自動生成中..."):
                try:
                    system_prompt, user_prompt = build_conversation_prompt(
                        st.session_state["transcription_result"],
                        st.session_state["emotion_coords"],
                    )

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.7,
                    )

                    st.session_state["ai_response"] = response.choices[
                        0
                    ].message.content

                    # 対話履歴に追加
                    st.session_state["conversation_history"].append(
                        {
                            "transcription": st.session_state["transcription_result"],
                            "emotion": st.session_state["emotion_coords"],
                            "ai_response": st.session_state["ai_response"],
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                    st.rerun()
                except Exception as e:
                    st.error(f"GPT API呼び出しエラー: {e}")

        # 既にAI応答が生成されている場合、手動で再生成できるボタンを表示
        elif (
            client is not None
            and "OPENAI_API_KEY" in st.secrets
            and st.session_state["ai_response"] is not None
        ):
            if st.button("🔄 AI応答を再生成", type="secondary"):
                st.session_state["ai_response"] = None
                st.rerun()
    elif st.session_state["transcription_status"] == "error":
        st.error("文字起こし処理中にエラーが発生しました。")

# AI応答の表示
if st.session_state["ai_response"]:
    st.markdown("---")
    st.subheader("💬 AI応答")
    st.info(st.session_state["ai_response"])

# 対話履歴の表示
if st.session_state["conversation_history"]:
    st.markdown("---")
    st.subheader("📚 対話履歴")
    for i, conv in enumerate(reversed(st.session_state["conversation_history"])):
        with st.expander(
            f"対話 {len(st.session_state['conversation_history']) - i} - {conv.get('timestamp', '')[:10]}"
        ):
            st.write(f"**感情座標:** {conv['emotion']}")
            st.write(f"**あなた:** {conv['transcription']}")
            st.write(f"**AI:** {conv['ai_response']}")
else:
    st.markdown("---")
    st.info(
        "まだ対話履歴がありません。録画・録音ページで録画し、文字起こし結果が表示されたら、ここでAI応答を生成できます。"
    )

# 格納済みデータの確認
st.markdown("---")
st.subheader("格納済みデータ（参照確認）")

video_buffer = st.session_state["video_buffer"]
audio_buffer = st.session_state["audio_buffer"]

st.write(f"- emotion_coords: `{st.session_state['emotion_coords']}`")
st.write(
    f"- video_buffer: `{None if video_buffer is None else (str(len(video_buffer)) + ' bytes')}`"
)
st.write(
    f"- audio_buffer: `{None if audio_buffer is None else (str(len(audio_buffer)) + ' bytes')}`"
)
st.write(
    f"- transcription_result: `{st.session_state['transcription_result'] if st.session_state['transcription_result'] else 'None'}`"
)
st.write(f"- transcription_status: `{st.session_state['transcription_status']}`")

# デバッグ表示
with st.expander("デバッグ：session_stateを見る"):
    st.json(
        {
            "emotion_coords": st.session_state["emotion_coords"],
            "is_recording": st.session_state["is_recording"],
            "recording_started_at": st.session_state["recording_started_at"],
            "video_buffer_len": None if video_buffer is None else len(video_buffer),
            "audio_buffer_len": None if audio_buffer is None else len(audio_buffer),
            "captured_frame": "set"
            if st.session_state["captured_frame"] is not None
            else None,
            "captured_audio": "set"
            if st.session_state["captured_audio"] is not None
            else None,
            "transcription_result": st.session_state["transcription_result"],
            "transcription_status": st.session_state["transcription_status"],
            "conversation_history_count": len(st.session_state["conversation_history"]),
        }
    )
