"""メインページ - ステップバイステップで自動進行"""

import os
import tempfile
import asyncio
import streamlit as st
from datetime import datetime
from aiortc.contrib.media import MediaRecorder
from streamlit_webrtc import WebRtcMode, webrtc_streamer, RTCConfiguration
from utils import (
    init_session_state,
    get_openai_client,
    save_conversation,
    get_ice_servers,
)
from services.transcription import transcribe_video
from services.face_analysis import analyze_face_emotion
from services.ai_chat import generate_ai_response

st.set_page_config(
    page_title="AI対話振り返りメディテーション 2",
    page_icon="🧘",
    layout="wide",
    initial_sidebar_state="collapsed",  # サイドバーを最初から閉じる
)


# asyncioの例外ハンドラーを設定して、aioiceの内部エラーを抑制
def suppress_aioice_errors(loop, context):
    """aioiceの内部エラーを抑制する例外ハンドラー"""
    exception = context.get("exception")
    message = context.get("message", "")

    if exception:
        error_msg = str(exception)
        error_type = type(exception).__name__

        # aioice/aiortcの内部エラーを無視
        if (
            "call_exception_handler" in error_msg
            or "is_alive" in error_msg
            or "sendto" in error_msg
            or "NoneType" in error_msg
            or "AttributeError" in error_type
            or "aioice" in error_msg.lower()
            or "aiortc" in error_msg.lower()
            or "Transaction.__retry" in error_msg
            or "Fatal write error" in error_msg
        ):
            # エラーを無視（ログに出力しない）
            return

    # メッセージからもチェック
    if message:
        if (
            "call_exception_handler" in message
            or "is_alive" in message
            or "sendto" in message
            or "aioice" in message.lower()
            or "aiortc" in message.lower()
        ):
            return

    # その他のエラーは標準のハンドラーに渡す（loopが存在する場合のみ）
    if loop and hasattr(loop, "default_exception_handler"):
        try:
            loop.default_exception_handler(context)
        except Exception:
            # デフォルトハンドラーも失敗する場合は無視
            pass


# 現在のイベントループに例外ハンドラーを設定
try:
    loop = asyncio.get_event_loop()
    if loop and not hasattr(loop, "_aioice_handler_set"):
        loop.set_exception_handler(suppress_aioice_errors)
        loop._aioice_handler_set = True
except RuntimeError:
    # イベントループが存在しない場合は無視
    pass
except Exception:
    # その他の例外も無視
    pass

# セッション状態の初期化
init_session_state()

# ユーザー名のチェックと入力フォーム
if "username" not in st.session_state or not st.session_state["username"]:
    st.title("🧘 AI対話振り返りメディテーション3")
    st.markdown("---")
    st.subheader("👤 ユーザー名を入力してください")
    st.markdown("対話履歴を保存するために、ユーザー名を入力してください。")

    with st.form("username_form"):
        username_input = st.text_input(
            "ユーザー名",
            placeholder="例: 山田太郎",
            help="このユーザー名で対話履歴が保存されます。",
        )
        submitted = st.form_submit_button("開始", type="primary")

        if submitted:
            if username_input and username_input.strip():
                username = username_input.strip()
                st.session_state["username"] = username
                # ユーザー名設定後、データベースから履歴を読み込み
                from utils import load_conversation_history

                st.session_state["conversation_history"] = load_conversation_history(
                    username
                )
                st.session_state["last_loaded_username"] = username
                st.success(f"ユーザー名「{username}」で開始します。")
                st.rerun()
            else:
                st.error("ユーザー名を入力してください。")

    st.stop()  # ユーザー名が設定されるまで処理を停止

# 現在のステップを管理（1: 感情入力, 2: 録画録音, 3: 対話結果）
if "current_step" not in st.session_state:
    st.session_state["current_step"] = 1

# OpenAIクライアントの取得
client = get_openai_client()

st.title("🧘 AI対話振り返りメディテーション（MVP）")
# ユーザー名の表示
st.caption(f"👤 ユーザー: {st.session_state['username']}")

# プログレスバー
steps = ["感情入力", "録画録音", "対話結果"]
progress = (st.session_state["current_step"] - 1) / len(steps)
st.progress(
    progress,
    text=f"ステップ {st.session_state['current_step']}/{len(steps)}: {steps[st.session_state['current_step'] - 1]}",
)

st.markdown("---")

# ============================
# ステップ1: 感情入力
# ============================
if st.session_state["current_step"] == 1:
    st.subheader("ステップ1: 🎭 感情入力")
    st.markdown("今の気持ちを6つのパラメータで入力してください。")

    # セッション状態から感情パラメータを取得（デフォルト値付き）
    emotion_params = st.session_state.get("emotion_params", {
        "pleasure": 0.0,
        "arousal": 0.0,
        "confidence": 0.0,
        "energy": 0.0,
        "productivity": 0.0,
        "redo_today": 0.0,
    })

    st.write("**① 今の感情を入力**")

    pleasure = st.slider(
        "快不快：不快 ← 0 → 快",
        min_value=-1.0,
        max_value=1.0,
        value=float(emotion_params.get("pleasure", 0.0)),
        step=0.01,
    )

    arousal = st.slider(
        "覚醒非覚醒：非覚醒（落ち着き） ← 0 → 覚醒",
        min_value=-1.0,
        max_value=1.0,
        value=float(emotion_params.get("arousal", 0.0)),
        step=0.01,
    )

    confidence = st.slider(
        "自信/不安：不安 ← 0 → 自信",
        min_value=-1.0,
        max_value=1.0,
        value=float(emotion_params.get("confidence", 0.0)),
        step=0.01,
    )

    energy = st.slider(
        "エネルギー/疲労：疲労 ← 0 → エネルギー",
        min_value=-1.0,
        max_value=1.0,
        value=float(emotion_params.get("energy", 0.0)),
        step=0.01,
    )

    productivity = st.slider(
        "生産性：低 ← 0 → 高",
        min_value=-1.0,
        max_value=1.0,
        value=float(emotion_params.get("productivity", 0.0)),
        step=0.01,
    )

    redo_today = st.slider(
        "今日をやり直したいか：やり直したい ← 0 → やり直したくない",
        min_value=-1.0,
        max_value=1.0,
        value=float(emotion_params.get("redo_today", 0.0)),
        step=0.01,
    )

    if st.button("この設定で決定 / 次へ進む", type="primary", use_container_width=True):
        st.session_state["emotion_params"] = {
            "pleasure": float(pleasure),
            "arousal": float(arousal),
            "confidence": float(confidence),
            "energy": float(energy),
            "productivity": float(productivity),
            "redo_today": float(redo_today),
        }
        st.session_state["current_step"] = 2
        st.success("感情パラメータを保存しました。")
        st.rerun()

# ============================
# ステップ2: 録画録音
# ============================
elif st.session_state["current_step"] == 2:
    st.subheader("ステップ2: 📹 録画・録音")
    st.markdown("録画を開始して、終了後に自動で分析へ進みます。")
    st.info(
        "💭 **今日一日、どんなことがありましたか？楽しかったこと、大変だったこと、何でも構いません。あなたの気持ちや考えを、1分ほど自由に話してみてください。**"
    )
    left2, right2 = st.columns([1, 1], gap="large")

    if (
        "recording_path" not in st.session_state
        or st.session_state["recording_path"] is None
    ):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
        st.session_state["recording_path"] = temp_file.name
        temp_file.close()

    # クロージャでrecording_pathをキャプチャ（別スレッドからアクセスするため）
    recording_path_value = st.session_state["recording_path"]

    def in_recorder_factory():
        return MediaRecorder(recording_path_value)

    with left2:
        st.write("**② 録画コントロール**")

        # webrtc_streamerの初期化（Twilio TURNサーバーを使用）
        # Twilioが設定されていない場合はSTUNサーバーのみを使用（フォールバック）
        ice_servers = get_ice_servers()
        ctx = webrtc_streamer(
            key="recorder",
            mode=WebRtcMode.SENDRECV,
            media_stream_constraints={"video": True, "audio": True},
            in_recorder_factory=in_recorder_factory,
            async_processing=True,
            rtc_configuration=RTCConfiguration({"iceServers": ice_servers}),
        )

        if ctx and ctx.state.playing and not st.session_state["was_playing"]:
            st.session_state["was_playing"] = True
            st.session_state["recording_started_at"] = datetime.now().isoformat(
                timespec="seconds"
            )
            st.session_state["recorded_video_data"] = None
            st.session_state["transcription_result"] = None
            st.session_state["transcription_status"] = "idle"
            st.session_state["face_emotion_result"] = None
            st.session_state["face_emotion_status"] = "idle"
            st.session_state["ai_response"] = None
            st.session_state["analysis_trigger"] = False

        if ctx and ctx.state.playing:
            st.info("録画中...")
        else:
            if st.session_state["was_playing"]:
                st.session_state["was_playing"] = False
                recording_path = st.session_state.get("recording_path")
                if recording_path and os.path.exists(recording_path):
                    file_size = os.path.getsize(recording_path)
                    st.write(f"録画ファイルサイズ: {file_size:,} bytes")
                    if file_size < 100:
                        st.warning(
                            "⚠️ 録画ファイルが小さすぎます。音声が録音されていない可能性があります。ブラウザのマイク許可を確認してください。"
                        )
                    with open(recording_path, "rb") as f:
                        recorded_bytes = f.read()
                    st.session_state["recorded_video_data"] = recorded_bytes
                    st.session_state["analysis_trigger"] = True
                    os.remove(recording_path)
                    st.session_state["recording_path"] = None
                    st.success("録画データを受け取りました。分析を開始します。")
                    st.rerun()
            st.info("停止中")

    with right2:
        st.write("**③ 状態**")
        if st.session_state["recording_started_at"]:
            st.write(f"開始時刻: {st.session_state['recording_started_at']}")
        st.info("録画を止めると自動で分析に進みます。")

        # 文字起こしが完了している場合、手動で次へ進むボタンを表示
        if st.session_state.get("transcription_status") == "completed":
            st.markdown("---")
            if st.button(
                "✅ 次のステップへ（対話結果）",
                type="primary",
                use_container_width=True,
                key="next_to_step3",
            ):
                st.session_state["current_step"] = 3
                st.rerun()

    # 録画データ受信後の自動分析
    if st.session_state.get("analysis_trigger"):
        st.session_state["analysis_trigger"] = False
        st.success("収録を停止しました。文字起こしと表情認識処理を開始します...")

        # 録画データがある場合、文字起こしと表情認識処理を自動実行
        if (
            st.session_state["recorded_video_data"] is not None
            and client is not None
            and "OPENAI_API_KEY" in st.secrets
        ):
            # 文字起こし処理
            with st.status(
                "録画データから音声を抽出して文字起こし中...", expanded=True
            ) as status:
                try:
                    st.write("動画ファイルを読み込んでいます...")
                    st.write("Whisper APIに送信中...（動画ファイルから音声を抽出）")
                    st.session_state["transcription_status"] = "processing"

                    # バックエンドサービスを呼び出し
                    transcription_text, transcription_status, error_msg = (
                        transcribe_video(
                            st.session_state["recorded_video_data"], client
                        )
                    )

                    if transcription_status == "completed":
                        st.session_state["transcription_result"] = transcription_text
                        st.session_state["transcription_status"] = "completed"
                        status.update(
                            label="文字起こし完了！",
                            state="complete",
                            expanded=False,
                        )
                    else:
                        st.session_state["transcription_status"] = "error"
                        st.error(
                            f"文字起こし処理中にエラーが発生しました\n詳細: {error_msg}"
                        )
                        status.update(label="エラー発生", state="error")
                except Exception as e:
                    st.session_state["transcription_status"] = "error"
                    import traceback

                    st.error(f"文字起こしエラー: {e}\n詳細: {traceback.format_exc()}")
                    status.update(label="エラー発生", state="error")

            # 表情認識処理
            with st.status(
                "録画データからフレームを抽出して表情認識中...", expanded=True
            ) as status_face:
                try:
                    st.write("動画ファイルから5秒ごとにフレームを抽出しています...")
                    st.write("GPT-4o Vision APIに送信中...")
                    st.session_state["face_emotion_status"] = "processing"

                    # バックエンドサービスを呼び出し
                    face_emotion, face_status, error_msg = analyze_face_emotion(
                        st.session_state["recorded_video_data"], client
                    )

                    if face_status == "completed":
                        st.session_state["face_emotion_result"] = face_emotion
                        st.session_state["face_emotion_status"] = "completed"
                        status_face.update(
                            label="表情認識完了！",
                            state="complete",
                            expanded=False,
                        )
                    else:
                        st.session_state["face_emotion_status"] = "error"
                        st.warning(
                            f"表情認識処理中にエラーが発生しました（続行します）\n詳細: {error_msg}"
                        )
                        st.session_state["face_emotion_result"] = None
                        status_face.update(
                            label="表情認識エラー（続行）",
                            state="error",
                            expanded=False,
                        )
                except Exception as e:
                    st.session_state["face_emotion_status"] = "error"
                    import traceback

                    st.warning(
                        f"表情認識エラー: {e}（続行します）\n詳細: {traceback.format_exc()}"
                    )
                    st.session_state["face_emotion_result"] = None
                    status_face.update(
                        label="表情認識エラー（続行）",
                        state="error",
                        expanded=False,
                    )

            # 文字起こしが完了したら自動的に次のステップへ（ここで遷移）
            if st.session_state["transcription_status"] == "completed":
                st.session_state["current_step"] = 3
                st.rerun()
        else:
            st.warning(
                "録画データが見つかりません。またはAPIキーが設定されていません。"
            )

# ============================
# ステップ3: 対話結果
# ============================
elif st.session_state["current_step"] == 3:
    st.subheader("ステップ3: 💬 対話・結果")
    st.markdown("文字起こし結果とAI応答を確認できます。")

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
                        # バックエンドサービスを呼び出し
                        emotion_params = st.session_state.get("emotion_params", {
                            "pleasure": 0.0,
                            "arousal": 0.0,
                            "confidence": 0.0,
                            "energy": 0.0,
                            "productivity": 0.0,
                            "redo_today": 0.0,
                        })
                        ai_response, response_status = generate_ai_response(
                            st.session_state["transcription_result"],
                            emotion_params,
                            face_emotion=st.session_state.get("face_emotion_result"),
                            client=client,
                        )

                        if response_status == "completed":
                            st.session_state["ai_response"] = ai_response

                            # 対話履歴に追加（データベースにも保存）
                            emotion_params = st.session_state.get("emotion_params", {
                                "pleasure": 0.0,
                                "arousal": 0.0,
                                "confidence": 0.0,
                                "energy": 0.0,
                                "productivity": 0.0,
                                "redo_today": 0.0,
                            })
                            conversation_data = {
                                "transcription": st.session_state[
                                    "transcription_result"
                                ],
                                "emotion": emotion_params,
                                "face_emotion": st.session_state.get(
                                    "face_emotion_result"
                                ),
                                "ai_response": st.session_state["ai_response"],
                                "timestamp": datetime.now().isoformat(),
                            }
                            save_conversation(
                                conversation_data, st.session_state.get("username")
                            )

                            st.rerun()
                        else:
                            st.error("AI応答生成に失敗しました")
                    except Exception as e:
                        st.error(f"AI応答生成エラー: {e}")
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
                emotion = conv.get("emotion", {})
                # 後方互換性: タプル形式の場合は表示
                if isinstance(emotion, (tuple, list)):
                    st.write(f"**感情パラメータ:** 快不快={emotion[0]:.2f}, 覚醒非覚醒={emotion[1]:.2f} (旧形式)")
                elif isinstance(emotion, dict):
                    st.write("**感情パラメータ:**")
                    st.write(f"- 快不快: {emotion.get('pleasure', 0.0):.2f}")
                    st.write(f"- 覚醒非覚醒: {emotion.get('arousal', 0.0):.2f}")
                    st.write(f"- 自信/不安: {emotion.get('confidence', 0.0):.2f}")
                    st.write(f"- エネルギー/疲労: {emotion.get('energy', 0.0):.2f}")
                    st.write(f"- 生産性: {emotion.get('productivity', 0.0):.2f}")
                    st.write(f"- 今日をやり直したいか: {emotion.get('redo_today', 0.0):.2f}")
                else:
                    st.write(f"**感情パラメータ:** {emotion}")
                
                if conv.get("face_emotion"):
                    face_info = conv["face_emotion"]
                    dominant = face_info.get("dominant_emotion", "unknown")
                    confidence = face_info.get("confidence", 0.0)
                    frame_count = face_info.get("frame_count", 0)
                    st.write(
                        f"**表情分析:** {dominant} (信頼度: {confidence:.2f}, 分析フレーム数: {frame_count})"
                    )
                st.write(f"**あなた:** {conv['transcription']}")
                st.write(f"**AI:** {conv['ai_response']}")

    # 最初からやり直すボタン
    st.markdown("---")
    if st.button("🔄 最初からやり直す", type="primary", use_container_width=True):
        st.session_state["current_step"] = 1
        st.session_state["is_recording"] = False
        st.session_state["transcription_result"] = None
        st.session_state["transcription_status"] = "idle"
        st.session_state["face_emotion_result"] = None
        st.session_state["face_emotion_status"] = "idle"
        st.session_state["ai_response"] = None
        st.rerun()
