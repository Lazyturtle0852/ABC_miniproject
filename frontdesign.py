"""メインページ - ステップバイステップで自動進行"""

import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from datetime import datetime
from utils import init_session_state, get_openai_client
from services.transcription import transcribe_video
from services.ai_chat import generate_ai_response

st.set_page_config(
    page_title="AI対話振り返りメディテーション MVP",
    page_icon="🧘",
    layout="wide",
    initial_sidebar_state="collapsed",  # サイドバーを最初から閉じる
)

# セッション状態の初期化
init_session_state()

# 現在のステップを管理（1: 感情入力, 2: 録画録音, 3: 対話結果）
if "current_step" not in st.session_state:
    st.session_state["current_step"] = 1

# OpenAIクライアントの取得
client = get_openai_client()

st.title("🧘 AI対話振り返りメディテーション（MVP）")

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
    st.markdown("カメラとマイクを使って、動画と音声を同時に録画します。")

    left2, right2 = st.columns([1, 1], gap="large")

    with left2:
        st.write("**② 収録コントロール**")

        if not st.session_state["is_recording"]:
            if st.button("▶️ スタート", use_container_width=True):
                st.session_state["is_recording"] = True
                st.session_state["recording_started_at"] = datetime.now().isoformat(
                    timespec="seconds"
                )
                st.session_state["video_buffer"] = None
                st.session_state["audio_buffer"] = None
                st.session_state["captured_frame"] = None
                st.session_state["captured_audio"] = None
                st.success("収録を開始しました")
                st.rerun()
        else:
            if st.button("⏹️ ストップ（収録完了）", use_container_width=True):
                st.session_state["is_recording"] = False

                if st.session_state["recorded_video_data"] is not None:
                    st.session_state["video_buffer"] = st.session_state[
                        "recorded_video_data"
                    ]
                    st.session_state["audio_buffer"] = st.session_state[
                        "recorded_video_data"
                    ]
                else:
                    if st.session_state["captured_frame"] is not None:
                        st.session_state["video_buffer"] = st.session_state[
                            "captured_frame"
                        ].getvalue()
                    else:
                        st.session_state["video_buffer"] = b""
                    if st.session_state["captured_audio"] is not None:
                        st.session_state["audio_buffer"] = st.session_state[
                            "captured_audio"
                        ].getvalue()
                    else:
                        st.session_state["audio_buffer"] = b""

                st.success("収録を停止しました。文字起こし処理を開始します...")

                # 録画データがある場合、文字起こし処理を自動実行
                if (
                    st.session_state["recorded_video_data"] is not None
                    and client is not None
                    and "OPENAI_API_KEY" in st.secrets
                ):
                    with st.status(
                        "録画データから音声を抽出して文字起こし中...", expanded=True
                    ) as status:
                        try:
                            st.write("動画ファイルを読み込んでいます...")
                            st.write(
                                "Whisper APIに送信中...（動画ファイルから音声を抽出）"
                            )
                            st.session_state["transcription_status"] = "processing"

                            # バックエンドサービスを呼び出し
                            transcription_text, transcription_status = transcribe_video(
                                st.session_state["recorded_video_data"], client
                            )

                            if transcription_status == "completed":
                                st.session_state["transcription_result"] = (
                                    transcription_text
                                )
                                st.session_state["transcription_status"] = "completed"
                                status.update(
                                    label="文字起こし完了！",
                                    state="complete",
                                    expanded=False,
                                )
                                # 文字起こしが完了したら自動的に次のステップへ（ここで遷移）
                                st.session_state["current_step"] = 3
                            else:
                                st.session_state["transcription_status"] = "error"
                                st.error("文字起こし処理中にエラーが発生しました")
                                status.update(label="エラー発生", state="error")
                        except Exception as e:
                            st.session_state["transcription_status"] = "error"
                            st.error(f"エラー: {e}")
                            status.update(label="エラー発生", state="error")

                    # ステップ遷移後、rerun
                    if st.session_state["transcription_status"] == "completed":
                        st.rerun()
                else:
                    st.warning(
                        "録画データが見つかりません。またはAPIキーが設定されていません。"
                    )

                st.rerun()

        if st.session_state["is_recording"]:
            st.warning(
                f"🔴 収録セッション開始中…（開始時刻: {st.session_state['recording_started_at']}）"
            )
        else:
            st.success("⏸️ 停止中")

    with right2:
        st.write("**③ 録画・録音**")

        if st.session_state["is_recording"]:
            st.info(
                "📹 下の録画UIで録画を開始してください。カメラとマイクが同時に起動します。"
            )

            html_code = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body { font-family: Arial, sans-serif; padding: 10px; }
                    #videoPreview { width: 100%; max-width: 640px; border: 2px solid #ddd; border-radius: 8px; }
                    #recordBtn, #stopBtn { padding: 10px 20px; font-size: 16px; margin: 5px; border-radius: 5px; border: none; cursor: pointer; }
                    #recordBtn { background-color: #ff4444; color: white; }
                    #recordBtn:hover { background-color: #cc0000; }
                    #stopBtn { background-color: #666; color: white; }
                    #stopBtn:hover { background-color: #444; }
                    #stopBtn:disabled { background-color: #ccc; cursor: not-allowed; }
                    .recording-indicator { display: inline-block; width: 12px; height: 12px; background-color: #ff4444; border-radius: 50%; animation: pulse 1.5s infinite; margin-right: 8px; }
                    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
                    #status { margin-top: 10px; padding: 10px; border-radius: 5px; }
                    .status-recording { background-color: #ffe6e6; color: #cc0000; }
                    .status-ready { background-color: #e6f3ff; color: #0066cc; }
                </style>
            </head>
            <body>
                <video id="videoPreview" autoplay muted playsinline></video>
                <div style="margin-top: 10px;">
                    <button id="recordBtn" onclick="startRecording()">🔴 録画開始</button>
                    <button id="stopBtn" onclick="stopRecording()" disabled>⏹ 録画停止</button>
                </div>
                <div id="status" class="status-ready">準備完了</div>
                <script>
                    let mediaRecorder;
                    let recordedChunks = [];
                    let stream;
                    const videoPreview = document.getElementById('videoPreview');
                    const recordBtn = document.getElementById('recordBtn');
                    const stopBtn = document.getElementById('stopBtn');
                    const statusDiv = document.getElementById('status');

                    async function startRecording() {
                        try {
                            stream = await navigator.mediaDevices.getUserMedia({
                                video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
                                audio: { echoCancellation: true, noiseSuppression: true }
                            });
                            videoPreview.srcObject = stream;
                            const options = { mimeType: 'video/webm;codecs=vp8,opus', videoBitsPerSecond: 2500000 };
                            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                                options.mimeType = 'video/webm';
                            }
                            mediaRecorder = new MediaRecorder(stream, options);
                            recordedChunks = [];
                            mediaRecorder.ondataavailable = (event) => {
                                if (event.data && event.data.size > 0) {
                                    recordedChunks.push(event.data);
                                }
                            };
                            mediaRecorder.onstop = () => {
                                const blob = new Blob(recordedChunks, { type: 'video/webm' });
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = url;
                                a.download = 'recording_' + new Date().getTime() + '.webm';
                                document.body.appendChild(a);
                                a.click();
                                document.body.removeChild(a);
                                URL.revokeObjectURL(url);
                                const reader = new FileReader();
                                reader.onloadend = () => {
                                    const base64data = reader.result;
                                    sessionStorage.setItem('recorded_video', base64data);
                                    window.parent.postMessage({type: 'recording_complete'}, '*');
                                };
                                reader.readAsDataURL(blob);
                                stream.getTracks().forEach(track => track.stop());
                                videoPreview.srcObject = null;
                            };
                            mediaRecorder.start(1000);
                            recordBtn.disabled = true;
                            stopBtn.disabled = false;
                            statusDiv.innerHTML = '<span class="recording-indicator"></span>録画中...';
                            statusDiv.className = 'status-recording';
                        } catch (err) {
                            console.error('Error:', err);
                            statusDiv.textContent = 'エラー: ' + err.message;
                        }
                    }
                    function stopRecording() {
                        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                            mediaRecorder.stop();
                            recordBtn.disabled = false;
                            stopBtn.disabled = true;
                            statusDiv.textContent = '録画を停止しました。データを処理中...';
                            statusDiv.className = 'status-ready';
                        }
                    }
                </script>
            </body>
            </html>
            """

            components.html(html_code, height=500)
            st.success(
                "✅ 録画が完了すると、自動的に動画ファイル（.webm形式）がダウンロードされます。"
            )
        else:
            st.info("収録を開始すると、ここにカメラ/音声の入力UIが出ます。")

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
                            face_emotion=None,  # 将来実装用
                            client=client,
                        )

                        if response_status == "completed":
                            st.session_state["ai_response"] = ai_response

                            # 対話履歴に追加
                            st.session_state["conversation_history"].append(
                                {
                                    "transcription": st.session_state[
                                        "transcription_result"
                                    ],
                                    "emotion": st.session_state["emotion_coords"],
                                    "ai_response": st.session_state["ai_response"],
                                    "timestamp": datetime.now().isoformat(),
                                }
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
                st.write(f"**感情座標:** {conv['emotion']}")
                st.write(f"**あなた:** {conv['transcription']}")
                st.write(f"**AI:** {conv['ai_response']}")

    # 最初からやり直すボタン
    st.markdown("---")
    if st.button("🔄 最初からやり直す", type="primary", use_container_width=True):
        st.session_state["current_step"] = 1
        st.session_state["is_recording"] = False
        st.session_state["transcription_result"] = None
        st.session_state["transcription_status"] = "idle"
        st.session_state["ai_response"] = None
        st.rerun()
