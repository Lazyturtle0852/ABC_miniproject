"""
映像処理モジュール
DeepFaceによる感情解析とstreamlit-webrtc連携
"""

import cv2
import numpy as np
from typing import Optional, Dict, Tuple
from deepface import DeepFace
import time


class VideoProcessor:
    """映像処理クラス"""
    
    def __init__(self, frame_skip: int = 30):
        """
        映像処理の初期化
        
        Args:
            frame_skip: 間引き処理のフレーム間隔（30フレームに1回）
        """
        self.frame_skip = frame_skip
        self.frame_count = 0
        self.last_emotion = None
        self.last_analysis_time = 0
        self.analysis_interval = 1.0  # 1秒に1回の解析も可能
    
    def process_frame(
        self,
        frame: np.ndarray
    ) -> Tuple[np.ndarray, Optional[str]]:
        """
        フレームを処理して感情を検出
        
        Args:
            frame: OpenCV形式のフレーム（BGR形式）
        
        Returns:
            (処理済みフレーム, 検出された感情)
        """
        self.frame_count += 1
        current_time = time.time()
        
        # 間引き処理: 30フレームに1回 または 1秒に1回
        should_analyze = (
            self.frame_count % self.frame_skip == 0 or
            (current_time - self.last_analysis_time) >= self.analysis_interval
        )
        
        if should_analyze:
            try:
                # DeepFaceによる感情解析
                result = DeepFace.analyze(
                    frame,
                    actions=['emotion'],
                    enforce_detection=False,  # 顔未検出でもエラーにしない
                    silent=True
                )
                
                # 結果の処理（DeepFaceはリストまたは辞書を返す場合がある）
                if isinstance(result, list):
                    result = result[0]
                
                # 最も高い感情を取得
                if 'dominant_emotion' in result:
                    emotion = result['dominant_emotion']
                    self.last_emotion = emotion
                    self.last_analysis_time = current_time
                else:
                    emotion = self.last_emotion or "Analyzing..."
            
            except Exception as e:
                # エラー時は前回の結果を維持
                print(f"感情解析エラー: {e}")
                emotion = self.last_emotion or "Analyzing..."
        else:
            # 解析しない場合は前回の結果を使用
            emotion = self.last_emotion or "Analyzing..."
        
        # フレームに感情ラベルを描画
        annotated_frame = self._draw_emotion_label(frame, emotion)
        
        return annotated_frame, emotion
    
    def _draw_emotion_label(
        self,
        frame: np.ndarray,
        emotion: str
    ) -> np.ndarray:
        """
        フレームに感情ラベルを描画
        
        Args:
            frame: 元のフレーム
            emotion: 検出された感情
        
        Returns:
            描画済みフレーム
        """
        annotated_frame = frame.copy()
        
        # 感情ラベルのテキスト
        text = f"Emotion: {emotion}"
        
        # テキストの位置とスタイル
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        color = (0, 255, 0)  # 緑色
        thickness = 2
        
        # テキストの背景（読みやすくするため）
        (text_width, text_height), baseline = cv2.getTextSize(
            text, font, font_scale, thickness
        )
        cv2.rectangle(
            annotated_frame,
            (10, 10),
            (10 + text_width + 10, 10 + text_height + 10),
            (0, 0, 0),
            -1
        )
        
        # テキストを描画
        cv2.putText(
            annotated_frame,
            text,
            (15, 15 + text_height),
            font,
            font_scale,
            color,
            thickness
        )
        
        return annotated_frame
    
    def get_current_emotion(self) -> Optional[str]:
        """
        現在の感情を取得
        
        Returns:
            検出された感情（まだ検出されていない場合はNone）
        """
        return self.last_emotion
    
    def reset(self):
        """フレームカウンターと状態をリセット"""
        self.frame_count = 0
        self.last_emotion = None
        self.last_analysis_time = 0

