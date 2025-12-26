# フロントエンド ↔ バックエンド データ形式定義書

このドキュメントは、`frontdesign.py`（フロントエンド）と`services/`（バックエンド）間でやり取りするデータの形式を定義します。

## データ形式一覧

### フロントエンド → バックエンド（入力）

#### 1. 録画データ（文字起こし用）

- **変数名**: `video_data`
- **型**: `bytes`
- **形式**: WebM形式の動画データ（音声含む）
- **取得方法**: `st.session_state["recorded_video_data"]`
- **制約**: 
  - Whisper APIの制限: 25MB以下
  - 形式: `video/webm`（VP8/VP9 + Opus/Vorbis）

#### 2. 感情座標（AI応答生成用）

- **変数名**: `emotion_coords`
- **型**: `tuple[float, float]`
- **形式**: `(x, y)` タプル
- **取得方法**: `st.session_state["emotion_coords"]`
- **値の範囲**:
  - `x`: -1.0（不快） ～ 1.0（快）
  - `y`: -1.0（非覚醒） ～ 1.0（覚醒）
- **例**: `(0.5, -0.3)` は「やや快で、やや落ち着き」

#### 3. 文字起こし結果（AI応答生成用）

- **変数名**: `transcription_text`
- **型**: `str`
- **取得方法**: `st.session_state["transcription_result"]`
- **制約**: 空文字列でないこと（バリデーション推奨）

#### 4. 顔感情データ（AI応答生成用）

- **変数名**: `face_emotion`
- **型**: `dict | None`
- **形式**: `{
    "emotions": list[str],  # 各フレームの感情リスト
    "dominant_emotion": str,  # 最も多い感情
    "confidence": float,  # 平均信頼度
    "frame_count": int  # 分析したフレーム数
  }` または `None`
- **取得方法**: `st.session_state["face_emotion_result"]`
- **例**: `{"emotions": ["happy", "neutral", "happy"], "dominant_emotion": "happy", "confidence": 0.75, "frame_count": 3}`

---

### バックエンド → フロントエンド（出力）

#### 1. 文字起こし結果

- **関数**: `services.transcription.transcribe_video()`
- **戻り値の型**: `tuple[str, str]`
- **形式**: `(transcription_text, status)`
  - `transcription_text`: 文字起こし結果のテキスト（エラー時は空文字列）
  - `status`: `"completed"` または `"error"`
- **例**: `("こんにちは、元気です", "completed")` または `("", "error")`

#### 2. 表情認識結果

- **関数**: `services.face_analysis.analyze_face_emotion()`
- **戻り値の型**: `tuple[dict | None, str]`
- **形式**: `(face_emotion_result, status)`
  - `face_emotion_result`: 表情認識結果の辞書またはNone（エラー時）
  - `status`: `"completed"` または `"error"`
- **例**: `({"emotions": ["happy", "neutral"], "dominant_emotion": "happy", "confidence": 0.75, "frame_count": 2}, "completed")` または `(None, "error")`

#### 3. AI応答結果

- **関数**: `services.ai_chat.generate_ai_response()`
- **戻り値の型**: `tuple[str, str]`
- **形式**: `(ai_response, status)`
  - `ai_response`: ChatGPTからの応答テキスト（エラー時は空文字列）
  - `status`: `"completed"` または `"error"`
- **例**: `("ありがとうございます。今日の気分はいかがですか？", "completed")` または `("", "error")`

---

## 関数シグネチャ

### `services.transcription.transcribe_video()`

```python
def transcribe_video(
    video_data: bytes,
    client: OpenAI
) -> tuple[str, str]:
    """
    録画データから音声を抽出して文字起こし
    
    Args:
        video_data: WebM形式の動画データ（bytes）
        client: OpenAIクライアントインスタンス
        
    Returns:
        (transcription_text, status) のタプル
        - transcription_text: 文字起こし結果のテキスト（エラー時は空文字列）
        - status: "completed" または "error"
        
    Raises:
        Exception: 重大なエラーが発生した場合（UI層でキャッチする想定）
    """
```

### `services.face_analysis.analyze_face_emotion()`

```python
def analyze_face_emotion(
    video_data: bytes,
    client: OpenAI,
    interval_seconds: float = 5.0
) -> tuple[dict | None, str]:
    """
    WebM録画データから表情認識を実行（GPT-4o Vision使用）
    
    Args:
        video_data: WebM形式の動画データ（bytes）
        client: OpenAIクライアントインスタンス
        interval_seconds: フレーム抽出間隔（秒、デフォルト: 5.0）
        
    Returns:
        (face_emotion_result, status) のタプル
        - face_emotion_result: {
            "emotions": list[str],  # 各フレームの感情リスト
            "dominant_emotion": str,  # 最も多い感情
            "confidence": float,  # 平均信頼度
            "frame_count": int  # 分析したフレーム数
          } または None（エラー時）
        - status: "completed" または "error"
        
    Raises:
        Exception: 重大なエラーが発生した場合（UI層でキャッチする想定）
    """
```

### `services.ai_chat.generate_ai_response()`

```python
def generate_ai_response(
    transcription_text: str,
    emotion_coords: tuple[float, float],
    face_emotion: dict | None = None,
    client: OpenAI | None = None
) -> tuple[str, str]:
    """
    AI応答を生成（プロンプト構築 + ChatGPT API呼び出し）
    
    Args:
        transcription_text: 文字起こし結果のテキスト（空文字列不可）
        emotion_coords: 感情座標タプル (x, y)。x, y は -1.0 ～ 1.0
        face_emotion: 顔感情分析結果（オプション）。形式: {
            "emotions": list[str],
            "dominant_emotion": str,
            "confidence": float,
            "frame_count": int
          }
        client: OpenAIクライアントインスタンス（Noneの場合は内部で取得）
        
    Returns:
        (ai_response, status) のタプル
        - ai_response: AI応答テキスト（エラー時は空文字列）
        - status: "completed" または "error"
        
    Raises:
        Exception: 重大なエラーが発生した場合（UI層でキャッチする想定）
    """
```

---

## 使用例

### フロントエンドでの使用例

```python
# frontdesign.py より

from services.transcription import transcribe_video
from services.ai_chat import generate_ai_response
from utils import get_openai_client

client = get_openai_client()

# 文字起こし処理
video_data = st.session_state["recorded_video_data"]  # bytes
transcription, trans_status = transcribe_video(video_data, client)
if trans_status == "completed":
    st.session_state["transcription_result"] = transcription
    st.session_state["transcription_status"] = "completed"
else:
    st.session_state["transcription_status"] = "error"

# 表情認識処理
face_emotion, face_status = analyze_face_emotion(video_data, client)
if face_status == "completed":
    st.session_state["face_emotion_result"] = face_emotion
else:
    st.session_state["face_emotion_result"] = None

# AI応答生成
transcription = st.session_state["transcription_result"]  # str
emotion_coords = st.session_state["emotion_coords"]  # tuple[float, float]
face_emotion = st.session_state.get("face_emotion_result")  # dict | None
response, status = generate_ai_response(
    transcription,
    emotion_coords,
    face_emotion=face_emotion,  # 表情データを追加
    client=client
)
if status == "completed":
    st.session_state["ai_response"] = response
else:
    st.error("AI応答生成に失敗しました")
```

---

## エラー処理

- **バックエンド**: エラー時は`status="error"`を返し、エラーメッセージはログ出力
- **フロントエンド**: `status == "error"`の場合、ユーザーにエラーメッセージを表示
- **重大なエラー**: `Exception`をraise（UI層で`try-except`でキャッチ）

---

## ステータス値の定義

- `"completed"`: 処理が正常に完了
- `"error"`: 処理中にエラーが発生

---

## 注意事項

1. **データのバリデーション**: フロントエンド側で基本的なバリデーションを行うこと（空文字列チェック、範囲チェックなど）
2. **エラーハンドリング**: バックエンド関数は`status`を返すが、重大なエラーは`Exception`をraiseすること
3. **一時ファイル**: 文字起こし処理と表情認識処理で作成する一時ファイルは、処理後に必ず削除すること
4. **表情認識**: 録画データから5秒ごとにフレームを抽出し、GPT-4o Visionで分析する。複数フレームの結果は集約して返す
5. **APIコスト**: GPT-4o Vision APIはフレーム数に応じてコストが発生する

