"""データベース操作モジュール - Supabase (PostgreSQL) への接続と操作"""

import json
import logging
import streamlit as st
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# psycopg2のインポート（オプショナル）
try:
    import psycopg2
    from psycopg2 import sql
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logger.warning("psycopg2がインストールされていません。データベース機能は使用できません。")


def get_db_connection():
    """Supabaseデータベースへの接続を取得"""
    if not PSYCOPG2_AVAILABLE:
        return None
    
    try:
        # secrets.tomlから接続情報を取得
        db_config = {
            "host": st.secrets.get("SUPABASE_DB_HOST"),
            "port": st.secrets.get("SUPABASE_DB_PORT", "5432"),
            "database": st.secrets.get("SUPABASE_DB_NAME", "postgres"),
            "user": st.secrets.get("SUPABASE_DB_USER"),
            "password": st.secrets.get("SUPABASE_DB_PASSWORD"),
        }
        
        # 必須項目のチェック
        if not all([db_config["host"], db_config["user"], db_config["password"]]):
            return None
        
        # 接続を試行
        conn = psycopg2.connect(**db_config)
        return conn
    except (KeyError, AttributeError, Exception) as e:
        logger.debug(f"データベース接続情報が設定されていません: {e}")
        return None


def is_db_available() -> bool:
    """データベースが利用可能かチェック"""
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        # 接続テスト
        conn.close()
        return True
    except Exception:
        return False


def init_database():
    """データベーステーブルを初期化（存在しない場合に作成）"""
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        with conn.cursor() as cur:
            # テーブル作成SQL
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS conversation_history (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                transcription TEXT,
                emotion_x REAL,
                emotion_y REAL,
                face_emotion TEXT,
                ai_response TEXT
            );
            """
            cur.execute(create_table_sql)
            
            # インデックス作成（パフォーマンス向上のため）
            create_index_sql = """
            CREATE INDEX IF NOT EXISTS idx_conversation_timestamp 
            ON conversation_history(timestamp DESC);
            """
            cur.execute(create_index_sql)
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"データベース初期化エラー: {e}")
        try:
            conn.close()
        except:
            pass
        return False


def save_conversation_to_db(conversation_data: Dict) -> bool:
    """対話履歴をデータベースに保存"""
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        # データの準備
        transcription = conversation_data.get("transcription", "")
        emotion = conversation_data.get("emotion", (0.0, 0.0))
        emotion_x = float(emotion[0]) if isinstance(emotion, (tuple, list)) else 0.0
        emotion_y = float(emotion[1]) if isinstance(emotion, (tuple, list)) else 0.0
        face_emotion = json.dumps(conversation_data.get("face_emotion")) if conversation_data.get("face_emotion") else None
        ai_response = conversation_data.get("ai_response", "")
        timestamp = conversation_data.get("timestamp")
        
        with conn.cursor() as cur:
            insert_sql = """
            INSERT INTO conversation_history 
            (timestamp, transcription, emotion_x, emotion_y, face_emotion, ai_response)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cur.execute(
                insert_sql,
                (timestamp, transcription, emotion_x, emotion_y, face_emotion, ai_response)
            )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"データベース保存エラー（メモリのみモード）: {e}")
        try:
            conn.close()
        except:
            pass
        return False


def load_conversation_history_from_db() -> List[Dict]:
    """データベースから対話履歴を読み込み"""
    conn = get_db_connection()
    if conn is None:
        return []
    
    try:
        with conn.cursor() as cur:
            select_sql = """
            SELECT timestamp, transcription, emotion_x, emotion_y, face_emotion, ai_response
            FROM conversation_history
            ORDER BY timestamp DESC
            LIMIT 100
            """
            cur.execute(select_sql)
            rows = cur.fetchall()
        
        conn.close()
        
        # データを辞書形式に変換
        history = []
        for row in rows:
            timestamp, transcription, emotion_x, emotion_y, face_emotion_json, ai_response = row
            face_emotion = None
            if face_emotion_json:
                try:
                    face_emotion = json.loads(face_emotion_json)
                except:
                    pass
            
            history.append({
                "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
                "transcription": transcription or "",
                "emotion": (float(emotion_x), float(emotion_y)),
                "face_emotion": face_emotion,
                "ai_response": ai_response or "",
            })
        
        return history
    except Exception as e:
        logger.warning(f"データベース読み込みエラー（メモリのみモード）: {e}")
        try:
            conn.close()
        except:
            pass
        return []
