"""
データベースモジュール
SQLiteを使用したログ保存機能
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional


class Database:
    """SQLiteデータベース管理クラス"""
    
    def __init__(self, db_path: str = "conversation_logs.db"):
        """
        データベース初期化
        
        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """データベースとテーブルの初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # logsテーブルの作成
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                user_voice_text TEXT,
                detected_emotion TEXT,
                ai_response TEXT
            )
        """)
        
        # インデックスの作成（検索高速化）
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id ON logs(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON logs(timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def save_log(
        self,
        user_id: str,
        user_voice_text: Optional[str],
        detected_emotion: Optional[str],
        ai_response: Optional[str]
    ) -> int:
        """
        ログを保存
        
        Args:
            user_id: ユーザーID
            user_voice_text: 文字起こし結果
            detected_emotion: DeepFace結果
            ai_response: AI返答
        
        Returns:
            保存されたログのID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO logs (user_id, timestamp, user_voice_text, detected_emotion, ai_response)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            datetime.now().isoformat(),
            user_voice_text,
            detected_emotion,
            ai_response
        ))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return log_id
    
    def load_logs(
        self,
        user_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        ログを読み込み
        
        Args:
            user_id: ユーザーID（Noneの場合は全ユーザー）
            limit: 取得件数の上限
        
        Returns:
            ログのリスト
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id:
            query = "SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC"
            params = (user_id,)
        else:
            query = "SELECT * FROM logs ORDER BY timestamp DESC"
            params = ()
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # カラム名を取得
        columns = [description[0] for description in cursor.description]
        
        # 辞書形式に変換
        logs = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        return logs
    
    def get_emotion_history(self, user_id: str) -> List[Dict]:
        """
        感情の履歴を取得（グラフ表示用）
        
        Args:
            user_id: ユーザーID
        
        Returns:
            感情履歴のリスト（timestamp, detected_emotion）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, detected_emotion
            FROM logs
            WHERE user_id = ? AND detected_emotion IS NOT NULL
            ORDER BY timestamp ASC
        """, (user_id,))
        
        rows = cursor.fetchall()
        history = [
            {"timestamp": row[0], "emotion": row[1]}
            for row in rows
        ]
        
        conn.close()
        return history

