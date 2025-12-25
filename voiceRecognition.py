import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()


def main():
    st.set_page_config(page_title="高視認性・音声認識テスト", layout="centered")

    # --- カスタムCSSでUIをリッチにする ---
    st.markdown(
        """
        <style>
        .status-box {
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 20px;
            border: 2px solid #ddd;
        }
        .recording-active {
            background-color: #ffebee;
            border-color: #ff1744;
            color: #d32f2f;
            animation: pulse 2s infinite;
        }
        .standby {
            background-color: #f5f5f5;
            color: #616161;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(255, 23, 68, 0.4); }
            70% { box-shadow: 0 0 0 20px rgba(255, 23, 68, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 23, 68, 0); }
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.title("🎙️ 音声認識プロトタイプ")

    # 1. API準備
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # 2. 状態表示パネル
    # 録音データがあるかどうかで表示を切り替える
    audio_data = st.audio_input("ここをクリックして録音を開始/停止してください")

    if audio_data is None:
        # 待機中（グレー）
        st.markdown(
            """
            <div class="status-box standby">
                <h2 style="margin:0;">⚪️ 待機中</h2>
                <p>マイクボタンを押すと録音が始まります</p>
            </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        # データ受信後（赤）
        st.markdown(
            """
            <div class="status-box recording-active">
                <h2 style="margin:0;">🔴 音声受信完了</h2>
                <p>文字起こし処理を開始します...</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

    # 3. メイン処理
    if audio_data is not None:
        with st.status("AI解析中...", expanded=True) as status:
            st.write("音声を読み込んでいます...")

            # 一時保存
            temp_file = "temp_recording.wav"
            with open(temp_file, "wb") as f:
                f.write(audio_data.read())

            try:
                st.write("Whisper APIに送信中...")
                with open(temp_file, "rb") as f:
                    response = client.audio.transcriptions.create(
                        model="whisper-1", file=f, language="ja"
                    )

                st.session_state.text_result = response.text
                status.update(label="解析完了！", state="complete", expanded=False)

            except Exception as e:
                st.error(f"エラー: {e}")
                status.update(label="エラー発生", state="error")
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

        # 結果表示
        if "text_result" in st.session_state:
            st.markdown("---")
            st.subheader("📝 文字起こし結果")
            st.success(st.session_state.text_result)

            # リセットボタン
            if st.button("もう一度録音する"):
                del st.session_state.text_result
                st.rerun()

    # --- 録音が起動しない人へのガイド ---
    with st.expander("⚠️ 録音ボタンが反応しない場合はこちら"):
        st.warning("ブラウザの設定でマイクが許可されていない可能性があります。")
        st.markdown("""
        1. **アドレスバーを確認**: 左上の「鍵マーク」をクリックして「マイク」が許可かチェック。
        2. **URLを確認**: localhost:8501 になっていますか？（`127.0.0.1`だと動かない場合があります）
        3. **再読み込み**: 設定を変えたらページを更新してください。
        """)


if __name__ == "__main__":
    main()
