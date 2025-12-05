#!/bin/bash
# セットアップスクリプト
# エラー時に停止
set -e

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# エラーハンドリング関数
error_exit() {
    echo -e "${RED}❌ エラー: $1${NC}" >&2
    exit 1
}

# 成功メッセージ関数
success_msg() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 情報メッセージ関数
info_msg() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 警告メッセージ関数
warning_msg() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo -e "${BLUE}🚀 AI対話振り返りメディテーションシステム セットアップ開始${NC}"
echo ""

# Pythonのバージョンチェック
echo "🔍 Pythonのバージョンを確認中..."
if ! command -v python3 &> /dev/null; then
    error_exit "Python3がインストールされていません。Python 3.10以上をインストールしてください。"
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    error_exit "Python 3.10以上が必要です。現在のバージョン: Python $PYTHON_VERSION"
fi

success_msg "Python $PYTHON_VERSION を検出しました"

# 必要なファイルの存在確認
echo ""
echo "📋 必要なファイルを確認中..."
if [ ! -f "requirements.txt" ]; then
    error_exit "requirements.txt が見つかりません"
fi
success_msg "requirements.txt を確認しました"

if [ ! -f ".env.example" ]; then
    warning_msg ".env.example が見つかりません（後で手動で作成できます）"
else
    success_msg ".env.example を確認しました"
fi

# 仮想環境の作成
echo ""
echo "📦 仮想環境をセットアップ中..."
if [ ! -d "venv" ]; then
    echo "   仮想環境を作成中..."
    if ! python3 -m venv venv; then
        error_exit "仮想環境の作成に失敗しました"
    fi
    success_msg "仮想環境を作成しました"
else
    info_msg "仮想環境は既に存在します"
fi

# 仮想環境を有効化
echo ""
echo "🔧 仮想環境を有効化中..."
if [ ! -f "venv/bin/activate" ]; then
    error_exit "仮想環境のactivateスクリプトが見つかりません"
fi

# 仮想環境内で実行するため、サブシェルで実行
(
    source venv/bin/activate
    
    # pipのアップグレード
    echo ""
    echo "⬆️  pipをアップグレード中..."
    if ! pip install --upgrade pip --quiet; then
        error_exit "pipのアップグレードに失敗しました"
    fi
    success_msg "pipをアップグレードしました"
    
    # 依存パッケージのインストール
    echo ""
    echo "📥 依存パッケージをインストール中..."
    echo "   （初回インストールには5〜10分かかる場合があります）"
    if ! pip install -r requirements.txt; then
        error_exit "パッケージのインストールに失敗しました"
    fi
    success_msg "依存パッケージのインストールが完了しました"
    
    # インストール確認
    echo ""
    echo "🔍 インストールを確認中..."
    if ! python3 -c "import streamlit" 2>/dev/null; then
        error_exit "streamlitのインストール確認に失敗しました"
    fi
    success_msg "主要パッケージのインストールを確認しました"
)

# .envファイルの作成
echo ""
echo "📝 環境変数ファイルをセットアップ中..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        success_msg ".envファイルを作成しました"
        warning_msg ".envファイルにOpenAI APIキーを設定してください"
    else
        warning_msg ".env.exampleが見つかりません。手動で.envファイルを作成してください"
    fi
else
    info_msg ".envファイルは既に存在します"
fi

# 完了メッセージ
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
success_msg "セットアップが完了しました！"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo "次のステップ:"
echo "1. .envファイルにOpenAI APIキーを設定してください"
echo "   （まだ設定していない場合）"
echo ""
echo "2. 仮想環境を有効化:"
echo "   ${BLUE}source venv/bin/activate${NC}"
echo ""
echo "3. アプリケーションを起動:"
echo "   ${BLUE}streamlit run app.py${NC}"
echo ""
echo "💡 ヒント: 仮想環境を有効化すると、プロンプトに (venv) が表示されます"
echo ""
