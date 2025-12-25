"""ページ1: 感情入力"""

import streamlit as st
import plotly.graph_objects as go
from utils import init_session_state

st.set_page_config(page_title="感情入力", layout="wide")

# セッション状態の初期化
init_session_state()

st.title("🎭 感情入力")

st.markdown("今の気持ちを2次元の感情プロットで入力してください。")

# レイアウト
left, right = st.columns([1, 1], gap="large")

# ----------------------------
# 1) 感情の2次元プロット入力
# ----------------------------
with left:
    st.subheader("① 今の感情を入力（2D）")

    # スライダー（-1〜1）
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

    # 決定ボタン（タプルで保存）
    if st.button("この座標で決定 / 保存", type="primary"):
        st.session_state["emotion_coords"] = (float(x), float(y))
        st.success(
            f"保存しました: emotion_coords = {st.session_state['emotion_coords']}"
        )

    st.caption(
        "保存された座標は st.session_state['emotion_coords'] に (x, y) のタプルで入ります。"
    )


with right:
    st.subheader("感情プロット（可視化・クリックで移動）")

    # Plotlyでインタラクティブなグラフを作成
    fig = go.Figure()

    # 背景にグリッドを追加（視覚的にわかりやすく）
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

    # 中央線（強調）
    fig.add_hline(y=0, line_width=2, line_color="black", opacity=0.5)
    fig.add_vline(x=0, line_width=2, line_color="black", opacity=0.5)

    # 現在の点をプロット（大きく目立つように）
    fig.add_trace(
        go.Scatter(
            x=[x],
            y=[y],
            mode="markers",
            marker=dict(
                size=20,
                color="red",
                line=dict(width=3, color="darkred"),
                symbol="circle",
            ),
            name="Current Emotion",
            showlegend=False,
            hovertemplate="<b>現在の座標</b><br>X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>",
        )
    )

    # 保存済みの点も表示（別色で、少し小さく）
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
                name="Saved",
                showlegend=False,
                hovertemplate="<b>保存済み座標</b><br>X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>",
            )
        )

    # 背景に細かいグリッドの点を配置（クリック可能にするため）
    grid_step = 0.1
    grid_x = [
        i * grid_step for i in range(int(-1.0 / grid_step), int(1.0 / grid_step) + 1)
    ]
    grid_y = [
        i * grid_step for i in range(int(-1.0 / grid_step), int(1.0 / grid_step) + 1)
    ]

    # 背景グリッド点を追加
    grid_x_points = []
    grid_y_points = []
    for gx in grid_x:
        for gy in grid_y:
            grid_x_points.append(gx)
            grid_y_points.append(gy)

    # グリッド点を追加（見えないがクリック可能）
    fig.add_trace(
        go.Scatter(
            x=grid_x_points,
            y=grid_y_points,
            mode="markers",
            marker=dict(
                size=8,
                opacity=0.01,
                color="gray",
            ),
            name="clickable_grid",
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # レイアウト設定
    fig.update_layout(
        xaxis=dict(
            range=[-1.1, 1.1],
            title="Pleasure (不快 ← 0 → 快)",
            zeroline=False,
            gridcolor="lightgray",
            gridwidth=0.5,
        ),
        yaxis=dict(
            range=[-1.1, 1.1],
            title="Arousal (非覚醒 ← 0 → 覚醒)",
            zeroline=False,
            gridcolor="lightgray",
            gridwidth=0.5,
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

    # グラフを表示（選択イベントを取得）
    selection = st.plotly_chart(
        fig, use_container_width=True, on_select="rerun", key="emotion_plot"
    )

    # グラフ上の点が選択された場合の処理
    if selection and hasattr(selection, "selection") and selection.selection.points:
        try:
            # 選択された点の座標を取得
            for point_data in selection.selection.points:
                if len(point_data) >= 2:
                    clicked_x = max(-1.0, min(1.0, float(point_data[0])))
                    clicked_y = max(-1.0, min(1.0, float(point_data[1])))
                    # 座標を更新
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
    st.caption(
        "💡 グラフ上の任意の位置をクリックすると、その位置の座標が自動保存されます。ズームやパンも可能です。"
    )

