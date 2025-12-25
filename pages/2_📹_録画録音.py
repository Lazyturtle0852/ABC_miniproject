"""ページ2: 録画・録音"""
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import os
from utils import init_session_state, get_openai_client

st.set_page_config(page_title="録画録音", layout="wide")

# セッション状態の初期化
init_session_state()

# OpenAIクライアントの取得
client = get_openai_client()

st.title("📹 録画・録音")

st.markdown("カメラとマイクを使って、動画と音声を同時に録画します。")

# ----------------------------
# 収録コントロール（トグル）
# ----------------------------
left2, right2 = st.columns([1, 1], gap="large")

with left2:
    st.subheader("② 収録コントロール")

    # トグルボタン（Start/Stop）
    if not st.session_state["is_recording"]:
        if st.button("▶️ スタート", use_container_width=True):
            st.session_state["is_recording"] = True
            st.session_state["recording_started_at"] = datetime.now().isoformat(
                timespec="seconds"
            )

            # 収録開始時に前回データをクリア
            st.session_state["video_buffer"] = None
            st.session_state["audio_buffer"] = None
            st.session_state["captured_frame"] = None
            st.session_state["captured_audio"] = None

            st.success("収録を開始しました")
    else:
        if st.button("⏹️ ストップ（収録完了）", use_container_width=True):
            st.session_state["is_recording"] = False

            # データ格納
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

            st.success("収録を停止し、video_buffer / audio_buffer に格納しました。")

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
                        temp_video_file = "temp_recording.webm"
                        with open(temp_video_file, "wb") as f:
                            f.write(st.session_state["recorded_video_data"])

                        st.write("動画ファイルを読み込んでいます...")
                        st.write("Whisper APIに送信中...（動画ファイルから音声を抽出）")
                        st.session_state["transcription_status"] = "processing"

                        with open(temp_video_file, "rb") as f:
                            response = client.audio.transcriptions.create(
                                model="whisper-1", file=f, language="ja"
                            )

                        st.session_state["transcription_result"] = response.text
                        st.session_state["transcription_status"] = "completed"
                        status.update(
                            label="文字起こし完了！", state="complete", expanded=False
                        )
                    except Exception as e:
                        st.session_state["transcription_status"] = "error"
                        st.error(f"エラー: {e}")
                        status.update(label="エラー発生", state="error")
                    finally:
                        if os.path.exists(temp_video_file):
                            os.remove(temp_video_file)
                
                # 文字起こしが完了したら自動的に対話結果ページに遷移
                if st.session_state["transcription_status"] == "completed":
                    st.info("✅ 文字起こしが完了しました。対話結果ページに移動します...")
                    st.switch_page("pages/3_💬_対話結果.py")

    # 録画中/停止中の状態表示
    if st.session_state["is_recording"]:
        st.warning(f"🔴 収録セッション開始中…（開始時刻: {st.session_state['recording_started_at']}）")
        st.markdown("**次のステップ：** 右側の録画UIで「🔴 録画開始」ボタンをクリックしてください。")
    else:
        st.success("⏸️ 停止中")
        st.markdown("**次のステップ：** 「▶️ スタート」ボタンをクリックして録画セッションを開始してください。")

    st.markdown("---")

    # 操作手順の説明
    with st.expander("📖 操作手順", expanded=not st.session_state["is_recording"]):
        st.markdown(
            """
        **録画の手順：**
        
        1. **「▶️ スタート」ボタンをクリック** → 録画UIが表示されます
        2. **録画UIで「🔴 録画開始」ボタンをクリック** → カメラとマイクが起動します
           - 初回はブラウザからカメラ・マイクの許可を求められます
           - 録画中は赤いインジケーターが点滅します
        3. **話したいことを話す** → 動画と音声が同時に録画されます
        4. **「⏹ 録画停止」ボタンをクリック** → 録画が停止され、ファイルがダウンロードされます
        5. **「⏹ ストップ（収録完了）」ボタンをクリック** → 録画データが保存され、文字起こし処理が実行されます
        
        **注意：** 録画完了後、自動的に動画ファイルがダウンロードされます。
        """
        )


with right2:
    st.subheader("③ 録画・録音")

    if st.session_state["is_recording"]:
        st.info("📹 下の録画UIで録画を開始してください。カメラとマイクが同時に起動します。")

        # カスタムHTMLコンポーネントで録画・録音
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

        # コンポーネントを表示
        components.html(html_code, height=500)

        st.success(
            "✅ 録画が完了すると、自動的に動画ファイル（.webm形式）がダウンロードされます。"
        )
        st.caption(
            "💡 録画中は赤いインジケーターが点滅します。録画を停止すると、データが処理されます。"
        )

    else:
        st.info("収録を開始すると、ここにカメラ/音声の入力UIが出ます。")

