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
    """Supabaseデータベースへの接続を取得（Supabase推奨のDATABASE_URL形式を優先）"""
    if not PSYCOPG2_AVAILABLE:
        return None
    
    try:
        # Supabase推奨のDATABASE_URL形式を優先的に使用
        database_url = st.secrets.get("DATABASE_URL")
        if database_url:
            # DATABASE_URLから直接接続
            conn = psycopg2.connect(database_url)
            return conn
        
        # 後方互換性のため、個別パラメータ形式もサポート
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
            # テーブル作成SQL（usernameカラムを含む）
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS conversation_history (
                id SERIAL PRIMARY KEY,
                username TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                transcription TEXT,
                emotion_x REAL,
                emotion_y REAL,
                face_emotion TEXT,
                ai_response TEXT
            );
            """
            cur.execute(create_table_sql)
            
            # 既存テーブルへのマイグレーション（usernameカラムが存在しない場合に追加）
            try:
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='conversation_history' AND column_name='username'
                """)
                if cur.fetchone() is None:
                    # usernameカラムが存在しない場合、追加
                    cur.execute("ALTER TABLE conversation_history ADD COLUMN username TEXT;")
                    logger.info("usernameカラムを追加しました")
            except Exception as e:
                logger.warning(f"マイグレーション処理中にエラーが発生しました: {e}")
            
            # インデックス作成（パフォーマンス向上のため）
            create_index_sql = """
            CREATE INDEX IF NOT EXISTS idx_conversation_timestamp 
            ON conversation_history(timestamp DESC);
            """
            cur.execute(create_index_sql)
            
            # usernameカラムのインデックス作成
            create_username_index_sql = """
            CREATE INDEX IF NOT EXISTS idx_conversation_username 
            ON conversation_history(username);
            """
            cur.execute(create_username_index_sql)
            
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


def save_conversation_to_db(conversation_data: Dict, username: str = None) -> bool:
    """対話履歴をデータベースに保存"""
    # usernameがNoneの場合は保存しない
    if username is None:
        logger.warning("usernameがNoneのため、データベースへの保存をスキップします")
        return False
    
    conn = get_db_connection()
    if conn is None:
        logger.warning("データベース接続が取得できませんでした")
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
            (username, timestamp, transcription, emotion_x, emotion_y, face_emotion, ai_response)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(
                insert_sql,
                (username, timestamp, transcription, emotion_x, emotion_y, face_emotion, ai_response)
            )
        
        conn.commit()
        conn.close()
        logger.info(f"データベースへの保存に成功しました（ユーザー名: {username}）")
        return True
    except Exception as e:
        logger.warning(f"データベース保存エラー（ユーザー名: {username}）: {e}")
        try:
            conn.close()
        except:
            pass
        return False


def load_conversation_history_from_db(username: str = None) -> List[Dict]:
    """データベースから対話履歴を読み込み（usernameでフィルタリング）"""
    if username is None:
        logger.warning("usernameがNoneのため、データベースからの読み込みをスキップします")
        return []
    
    conn = get_db_connection()
    if conn is None:
        logger.warning("データベース接続が取得できませんでした")
        return []
    
    try:
        with conn.cursor() as cur:
            # usernameでフィルタリング
            select_sql = """
            SELECT timestamp, transcription, emotion_x, emotion_y, face_emotion, ai_response
            FROM conversation_history
            WHERE username = %s
            ORDER BY timestamp DESC
            LIMIT 100
            """
            cur.execute(select_sql, (username,))
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
        
        logger.info(f"データベースから{len(history)}件の履歴を読み込みました（ユーザー名: {username}）")
        return history
    except Exception as e:
        logger.warning(f"データベース読み込みエラー（ユーザー名: {username}）: {e}")
        try:
            conn.close()
        except:
            pass
        return []
