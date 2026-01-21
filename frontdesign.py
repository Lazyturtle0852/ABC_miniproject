"""メインページ - ステップバイステップで自動進行"""

import os
import tempfile
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from aiortc.contrib.media import MediaRecorder
from streamlit_webrtc import WebRtcMode, webrtc_streamer
from utils import init_session_state, get_openai_client, save_conversation
from services.transcription import transcribe_video
from services.face_analysis import analyze_face_emotion
from services.ai_chat import generate_ai_response

st.set_page_config(
    page_title="AI対話振り返りメディテーション MVP",
    page_icon="🧘",
    layout="wide",
    initial_sidebar_state="collapsed",  # サイドバーを最初から閉じる
)

# セッション状態の初期化
init_session_state()

# ユーザー名のチェックと入力フォーム
if "username" not in st.session_state or not st.session_state["username"]:
    st.title("🧘 AI対話振り返りメディテーション（MVP）")
    st.markdown("---")
    st.subheader("👤 ユーザー名を入力してください")
    st.markdown("対話履歴を保存するために、ユーザー名を入力してください。")
    
    with st.form("username_form"):
        username_input = st.text_input(
            "ユーザー名",
            placeholder="例: 山田太郎",
            help="このユーザー名で対話履歴が保存されます。"
        )
        submitted = st.form_submit_button("開始", type="primary")
        
        if submitted:
            if username_input and username_input.strip():
                username = username_input.strip()
                st.session_state["username"] = username
                # ユーザー名設定後、データベースから履歴を読み込み
                from utils import load_conversation_history
                st.session_state["conversation_history"] = load_conversation_history(username)
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
    st.markdown("今の気持ちを2次元の感情プロットで入力してください。")

    left, right = st.columns([1, 1], gap="large")

    with left:
        st.write("**① 今の感情を入力（2D）**")

        x = st.slider(
            "X軸：不快 ← 0 → 快",
            min_value=-1.0,
            max_value=1.0,
            value=float(st.session_state["emotion_coords"][0]),
            step=0.01,
        )
        y = st.slider(
            "Y軸：非覚醒（落ち着き） ← 0 → 覚醒",
            min_value=-1.0,
            max_value=1.0,
            value=float(st.session_state["emotion_coords"][1]),
            step=0.01,
        )

        if st.button(
            "この座標で決定 / 次へ進む", type="primary", use_container_width=True
        ):
            st.session_state["emotion_coords"] = (float(x), float(y))
            st.session_state["current_step"] = 2
            st.success(f"保存しました: {st.session_state['emotion_coords']}")
            st.rerun()

    with right:
        st.write("**感情プロット（可視化・クリックで移動）**")

        # Plotlyグラフ作成
        fig = go.Figure()

        # 背景グリッド
        for i in range(-1, 2):
            if i != 0:
                fig.add_hline(
                    y=i * 0.5,
                    line_width=0.5,
                    line_color="lightgray",
                    line_dash="dot",
                    opacity=0.3,
                )
                fig.add_vline(
                    x=i * 0.5,
                    line_width=0.5,
                    line_color="lightgray",
                    line_dash="dot",
                    opacity=0.3,
                )

        fig.add_hline(y=0, line_width=2, line_color="black", opacity=0.5)
        fig.add_vline(x=0, line_width=2, line_color="black", opacity=0.5)

        # 現在の点
        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y],
                mode="markers",
                marker=dict(size=20, color="red", line=dict(width=3, color="darkred")),
                showlegend=False,
                hovertemplate="<b>現在の座標</b><br>X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>",
            )
        )

        # 保存済みの点
        saved_x, saved_y = st.session_state["emotion_coords"]
        if abs(saved_x - x) > 0.01 or abs(saved_y - y) > 0.01:
            fig.add_trace(
                go.Scatter(
                    x=[saved_x],
                    y=[saved_y],
                    mode="markers",
                    marker=dict(
                        size=15,
                        color="lightblue",
                        line=dict(width=2, color="blue"),
                        opacity=0.7,
                        symbol="circle-open",
                    ),
                    showlegend=False,
                    hovertemplate="<b>保存済み座標</b><br>X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>",
                )
            )

        # クリック可能なグリッド
        grid_step = 0.1
        grid_x_points = [
            i * grid_step
            for i in range(int(-1.0 / grid_step), int(1.0 / grid_step) + 1)
        ]
        grid_y_points = [
            i * grid_step
            for i in range(int(-1.0 / grid_step), int(1.0 / grid_step) + 1)
        ]
        grid_x_all = [gx for gx in grid_x_points for _ in grid_y_points]
        grid_y_all = [gy for gy in grid_y_points for _ in grid_x_points]

        fig.add_trace(
            go.Scatter(
                x=grid_x_all,
                y=grid_y_all,
                mode="markers",
                marker=dict(size=8, opacity=0.01, color="gray"),
                showlegend=False,
                hoverinfo="skip",
            )
        )

        fig.update_layout(
            xaxis=dict(
                range=[-1.1, 1.1], title="Pleasure (不快 ← 0 → 快)", zeroline=False
            ),
            yaxis=dict(
                range=[-1.1, 1.1],
                title="Arousal (非覚醒 ← 0 → 覚醒)",
                zeroline=False,
                scaleanchor="x",
                scaleratio=1,
            ),
            title="Current Emotion Point (グラフ上をクリックして移動)",
            width=500,
            height=500,
            dragmode="select",
            hovermode="closest",
            plot_bgcolor="white",
            paper_bgcolor="white",
        )

        selection = st.plotly_chart(
            fig, use_container_width=True, on_select="rerun", key="emotion_plot"
        )

        if selection and hasattr(selection, "selection") and selection.selection.points:
            try:
                for point_data in selection.selection.points:
                    if len(point_data) >= 2:
                        clicked_x = max(-1.0, min(1.0, float(point_data[0])))
                        clicked_y = max(-1.0, min(1.0, float(point_data[1])))
                        st.session_state["emotion_coords"] = (clicked_x, clicked_y)
                        st.success(
                            f"座標を更新しました: ({clicked_x:.2f}, {clicked_y:.2f})"
                        )
                        st.rerun()
                        break
            except (AttributeError, IndexError, ValueError):
                pass

        st.info(
            f"スライダー現在値: (x, y)=({x:.2f}, {y:.2f}) / 保存済み: {st.session_state['emotion_coords']}"
        )

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
        try:
            ctx = webrtc_streamer(
                key="recorder",
                mode=WebRtcMode.SENDRECV,
                media_stream_constraints={"video": True, "audio": True},
                in_recorder_factory=in_recorder_factory,
                async_processing=True,
            )

            # ctxとctx.stateがNoneでないことを確認してからアクセス
            if ctx is not None and ctx.state is not None:
                is_playing = ctx.state.playing
                
                if is_playing and not st.session_state["was_playing"]:
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

                if is_playing:
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
            else:
                st.info("WebRTC接続を初期化中...")
        except (AttributeError, RuntimeError) as e:
            # WebRTC接続のエラーをキャッチして処理を続行
            st.warning(f"WebRTC接続でエラーが発生しました: {e}")
            if st.session_state.get("was_playing"):
                # 録画が停止した場合の処理
                st.session_state["was_playing"] = False
                recording_path = st.session_state.get("recording_path")
                if recording_path and os.path.exists(recording_path):
                    try:
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
                    except Exception as cleanup_error:
                        st.error(f"録画ファイルの処理中にエラーが発生しました: {cleanup_error}")
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
                    transcription_text, transcription_status = transcribe_video(
                        st.session_state["recorded_video_data"], client
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
                        st.error("文字起こし処理中にエラーが発生しました")
                        status.update(label="エラー発生", state="error")
                except Exception as e:
                    st.session_state["transcription_status"] = "error"
                    st.error(f"文字起こしエラー: {e}")
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
                    face_emotion, face_status = analyze_face_emotion(
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
                        st.warning("表情認識処理中にエラーが発生しました（続行します）")
                        st.session_state["face_emotion_result"] = None
                        status_face.update(
                            label="表情認識エラー（続行）",
                            state="error",
                            expanded=False,
                        )
                except Exception as e:
                    st.session_state["face_emotion_status"] = "error"
                    st.warning(f"表情認識エラー: {e}（続行します）")
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
                        ai_response, response_status = generate_ai_response(
                            st.session_state["transcription_result"],
                            st.session_state["emotion_coords"],
                            face_emotion=st.session_state.get("face_emotion_result"),
                            client=client,
                        )

                        if response_status == "completed":
                            st.session_state["ai_response"] = ai_response

                            # 対話履歴に追加（データベースにも保存）
                            conversation_data = {
                                "transcription": st.session_state[
                                    "transcription_result"
                                ],
                                "emotion": st.session_state["emotion_coords"],
                                "face_emotion": st.session_state.get(
                                    "face_emotion_result"
                                ),
                                "ai_response": st.session_state["ai_response"],
                                "timestamp": datetime.now().isoformat(),
                            }
                            save_conversation(conversation_data, st.session_state.get("username"))

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
                st.write(f"**感情座標:** {conv['emotion']}")
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
