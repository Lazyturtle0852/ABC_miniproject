import streamlit as st
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(layout="wide")

st.title("❤️ 感情入力インターフェース")
st.caption("スライダーを動かして、今の気分の位置（XY座標）を決めてください。")

# 画面を左右に分割（左：入力、右：マップ）
col_input, col_map = st.columns([1, 2])

with col_input:
    st.subheader("1. 今の気分は？")
    st.write("マップを見ながら位置を調整してください。")

    # X軸: Valence (快 - 不快)
    # 値を変えるとsession_stateなどを使わなくても再描画され、グラフに反映されます
    valence = st.slider(
        "↔️ 快 - 不快 (Valence)",
        min_value=-1.0,
        max_value=1.0,
        value=0.0,
        step=0.1,
        help="右(1.0)に行くほどポジティブ、左(-1.0)に行くほどネガティブ",
    )

    # Y軸: Arousal (覚醒 - 沈静)
    arousal = st.slider(
        "↕️ 覚醒 - 沈静 (Arousal)",
        min_value=-1.0,
        max_value=1.0,
        value=0.0,
        step=0.1,
        help="上(1.0)に行くほど興奮/活動的、下(-1.0)に行くほどリラックス/眠い",
    )

    diary = st.text_area("📝 ひとこと日記", placeholder="今の気持ちや出来事を書いてね")

    if st.button("この位置で記録する", type="primary"):
        # 本来はここでデータベース保存処理を行う
        st.success(f"記録しました！\n座標: ({valence}, {arousal})\n日記: {diary}")
        st.balloons()

with col_map:
    st.subheader("2. 感情マップ確認")

    # Plotlyグラフ作成
    fig = go.Figure()

    # 1. 現在の入力位置をプロット（動くマーカー）
    # スライダーの値(valence, arousal)をここに渡すことでリアルタイムに動きます
    fig.add_trace(
        go.Scatter(
            x=[valence],
            y=[arousal],
            mode="markers+text",
            text=["<b>YOU</b>"],
            textposition="top center",
            marker=dict(
                size=30,
                color="red",
                symbol="star",  # 星型にして目立たせる
                line=dict(width=2, color="white"),
            ),
            name="Current Mood",
            hoverinfo="skip",  # ホバー不要
        )
    )

    # 2. 過去のデータ（参考として薄く表示）
    # 本来はDBから取得
    past_data = {
        "x": [0.8, -0.6, -0.8, 0.2],
        "y": [0.6, 0.8, -0.5, -0.2],
        "date": ["12/01", "12/02", "12/03", "12/04"],
    }
    fig.add_trace(
        go.Scatter(
            x=past_data["x"],
            y=past_data["y"],
            mode="markers",
            text=past_data["date"],
            marker=dict(size=12, color="gray", opacity=0.4),
            name="History",
            hovertemplate="過去: %{text}<extra></extra>",
        )
    )

    # 3. 背景の4象限設定（ラッセルの円環モデル）
    fig.update_layout(
        xaxis=dict(
            title="不快 <----> 快 (Valence)",
            range=[-1.1, 1.1],
            zeroline=True,
            zerolinewidth=2,
        ),
        yaxis=dict(
            title="沈静 <----> 覚醒 (Arousal)",
            range=[-1.1, 1.1],
            zeroline=True,
            zerolinewidth=2,
        ),
        height=600,
        showlegend=False,
        margin=dict(l=20, r=20, t=20, b=20),
        # ユーザーが動かすのはスライダーなので、グラフ自体のズーム等は固定しても良い
        dragmode=False,
    )

    # 象限ラベル（色付き文字）
    fig.add_annotation(
        x=0.9,
        y=0.9,
        text="<b>High Energy<br>Positive</b>",
        showarrow=False,
        font=dict(color="orange", size=16),
    )
    fig.add_annotation(
        x=-0.9,
        y=0.9,
        text="<b>High Energy<br>Negative</b>",
        showarrow=False,
        font=dict(color="red", size=16),
    )
    fig.add_annotation(
        x=-0.9,
        y=-0.9,
        text="<b>Low Energy<br>Negative</b>",
        showarrow=False,
        font=dict(color="blue", size=16),
    )
    fig.add_annotation(
        x=0.9,
        y=-0.9,
        text="<b>Low Energy<br>Positive</b>",
        showarrow=False,
        font=dict(color="green", size=16),
    )

    # 背景色（オプショナル：象限ごとに薄く色をつける場合）
    # fig.add_shape(type="rect", x0=0, y0=0, x1=1.1, y1=1.1, fillcolor="orange", opacity=0.1, layer="below", line_width=0)
    # fig.add_shape(type="rect", x0=-1.1, y0=0, x1=0, y1=1.1, fillcolor="red", opacity=0.1, layer="below", line_width=0)
    # fig.add_shape(type="rect", x0=-1.1, y0=-1.1, x1=0, y1=0, fillcolor="blue", opacity=0.1, layer="below", line_width=0)
    # fig.add_shape(type="rect", x0=0, y0=-1.1, x1=1.1, y1=0, fillcolor="green", opacity=0.1, layer="below", line_width=0)

    st.plotly_chart(fig, use_container_width=True)
