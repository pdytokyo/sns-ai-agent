"""
jet_cut.py - 動画の無音部分を自動的に検出・カットするスクリプト

このスクリプトは指定された動画ファイル（MP4）の無音部分を自動的に検出し、
それらの部分をカットした新しい動画ファイルを生成します。

使用ライブラリ:
- moviepy: 動画処理
- librosa: 音声分析
- numpy: 数値計算
"""

import os
import sys
import tempfile
import numpy as np
from moviepy import VideoFileClip, concatenate_videoclips
import librosa
import time


def extract_audio(video_path, output_audio_path):
    """
    動画ファイルから音声を抽出し、WAVファイルとして保存します。
    
    Args:
        video_path (str): 入力動画ファイルのパス
        output_audio_path (str): 出力音声ファイルのパス
        
    Returns:
        bool: 処理が成功したかどうか
    """
    try:
        print(f"音声を抽出中: {video_path}")
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(output_audio_path)
        return True
    except Exception as e:
        print(f"音声抽出中にエラーが発生しました: {str(e)}")
        return False


def detect_non_silent_chunks(audio_path, silence_threshold=0.02, chunk_duration=0.1, margin=0.1):
    """
    音声ファイルから無音でない部分を検出します。
    
    Args:
        audio_path (str): 音声ファイルのパス
        silence_threshold (float): 無音と判断する閾値
        chunk_duration (float): 最短クリップ時間（秒）
        margin (float): 無音でない部分の前後に追加するマージン時間（秒）
        
    Returns:
        list: 無音でない部分の時間範囲のリスト [(開始時間, 終了時間), ...]
    """
    try:
        print(f"無音部分を検出中...")
        y, sr = librosa.load(audio_path, sr=None)
        
        audio_duration = len(y) / sr
        print(f"音声の長さ: {audio_duration:.2f}秒")
        
        amplitude = np.abs(y)
        
        chunk_size = int(chunk_duration * sr)
        num_chunks = len(amplitude) // chunk_size
        
        print(f"音声を分析中: 0/{num_chunks}チャンク (0%)")
        
        is_silent = []
        for i in range(num_chunks):
            if i % (num_chunks // 10) == 0 and i > 0:
                progress = (i / num_chunks) * 100
                print(f"音声を分析中: {i}/{num_chunks}チャンク ({progress:.1f}%)")
                
            chunk = amplitude[i * chunk_size:(i + 1) * chunk_size]
            is_silent.append(np.mean(chunk) < silence_threshold)
        
        print(f"音声を分析中: {num_chunks}/{num_chunks}チャンク (100%)")
        
        non_silent_chunks = []
        start_time = None
        
        for i, silent in enumerate(is_silent):
            time = i * chunk_duration
            
            if not silent and start_time is None:
                start_time = time
            elif silent and start_time is not None:
                non_silent_chunks.append((start_time, time))
                start_time = None
        
        if start_time is not None:
            non_silent_chunks.append((start_time, num_chunks * chunk_duration))
        
        merged_chunks = []
        if non_silent_chunks:
            current_start, current_end = non_silent_chunks[0]
            
            for start, end in non_silent_chunks[1:]:
                if start - current_end < chunk_duration:
                    current_end = end
                else:
                    merged_chunks.append((current_start, current_end))
                    current_start, current_end = start, end
            
            merged_chunks.append((current_start, current_end))
        
        margin_chunks = []
        for start, end in merged_chunks:
            margin_start = max(0, start - margin)
            margin_end = min(audio_duration, end + margin)
            margin_chunks.append((margin_start, margin_end))
        
        print(f"検出された無音でない部分: {len(margin_chunks)}個")
        return margin_chunks
    
    except Exception as e:
        print(f"無音部分の検出中にエラーが発生しました: {str(e)}")
        return []


def create_cut_video(video_path, output_path, non_silent_chunks):
    """
    無音でない部分を結合して新しい動画を作成します。
    
    Args:
        video_path (str): 入力動画ファイルのパス
        output_path (str): 出力動画ファイルのパス
        non_silent_chunks (list): 無音でない部分の時間範囲のリスト [(開始時間, 終了時間), ...]
        
    Returns:
        bool: 処理が成功したかどうか
    """
    try:
        if not non_silent_chunks:
            print("無音でない部分が検出されませんでした。処理を中止します。")
            return False
        
        print(f"無音部分をカットした動画を作成中...")
        video = VideoFileClip(video_path)
        
        total_duration = video.duration
        print(f"元の動画の長さ: {total_duration:.2f}秒")
        
        non_silent_duration = sum(end - start for start, end in non_silent_chunks)
        print(f"無音でない部分の合計時間: {non_silent_duration:.2f}秒")
        print(f"カット率: {(1 - non_silent_duration / total_duration) * 100:.1f}%")
        
        clips = []
        print(f"クリップを抽出中: 0/{len(non_silent_chunks)} (0%)")
        for i, (start, end) in enumerate(non_silent_chunks):
            if i % max(1, len(non_silent_chunks) // 5) == 0 and i > 0:
                progress = (i / len(non_silent_chunks)) * 100
                print(f"クリップを抽出中: {i}/{len(non_silent_chunks)} ({progress:.1f}%)")
            
            clip = VideoFileClip(video_path).subclipped(start, end)
            clips.append(clip)
        
        print(f"クリップを抽出中: {len(non_silent_chunks)}/{len(non_silent_chunks)} (100%)")
        
        print("クリップを結合中...")
        final_clip = concatenate_videoclips(clips)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"動画を保存中...")
        start_time = time.time()
        
        def progress_callback(t):
            elapsed = time.time() - start_time
            if elapsed > 0:
                fps = t / elapsed
                remaining = (final_clip.duration - t) / fps if fps > 0 else 0
                print(f"保存中: {t:.1f}/{final_clip.duration:.1f}秒 ({t/final_clip.duration*100:.1f}%) "
                      f"残り約{remaining:.1f}秒")
        
        print(f"動画を保存中... (この処理には時間がかかる場合があります)")
        
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=None,
            remove_temp=True
        )
        
        video.close()
        final_clip.close()
        for clip in clips:
            clip.close()
        
        print(f"処理が完了しました。出力ファイル: {output_path}")
        return True
    
    except Exception as e:
        print(f"動画作成中にエラーが発生しました: {str(e)}")
        return False


def process_video(input_video_path, output_video_path, silence_threshold=0.02, chunk_duration=0.1, margin=0.1):
    """
    動画の無音部分を検出・カットする処理を実行します。
    
    Args:
        input_video_path (str): 入力動画ファイルのパス
        output_video_path (str): 出力動画ファイルのパス
        silence_threshold (float): 無音と判断する閾値
        chunk_duration (float): 最短クリップ時間（秒）
        margin (float): 無音でない部分の前後に追加するマージン時間（秒）
        
    Returns:
        bool: 処理が成功したかどうか
    """
    if not os.path.exists(input_video_path):
        print(f"エラー: 入力ファイルが見つかりません: {input_video_path}")
        return False
    
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
    
    start_time = time.time()
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
        temp_audio_path = temp_audio_file.name
    
    try:
        if not extract_audio(input_video_path, temp_audio_path):
            return False
        
        non_silent_chunks = detect_non_silent_chunks(
            temp_audio_path,
            silence_threshold=silence_threshold,
            chunk_duration=chunk_duration,
            margin=margin
        )
        
        result = create_cut_video(input_video_path, output_video_path, non_silent_chunks)
        
        elapsed_time = time.time() - start_time
        print(f"総処理時間: {elapsed_time:.2f}秒")
        
        return result
        
    finally:
        if os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
                print(f"一時ファイルを削除しました: {temp_audio_path}")
            except Exception as e:
                print(f"一時ファイルの削除中にエラーが発生しました: {str(e)}")


def main():
    """
    メイン処理を実行します。
    """
    try:
        input_video_path = "videos/input.mp4"
        output_video_path = "output/jet_cut_output.mp4"
        silence_threshold = 0.02  # 無音と判断する閾値
        chunk_duration = 0.1      # 最短クリップ時間（秒）
        margin = 0.1              # 無音でない部分の前後に追加するマージン時間（秒）
        
        print("=== ジェットカット処理開始 ===")
        print(f"入力ファイル: {input_video_path}")
        print(f"出力ファイル: {output_video_path}")
        print(f"無音閾値: {silence_threshold}")
        print(f"最短クリップ時間: {chunk_duration}秒")
        print(f"マージン: {margin}秒")
        print("===========================")
        
        success = process_video(
            input_video_path,
            output_video_path,
            silence_threshold=silence_threshold,
            chunk_duration=chunk_duration,
            margin=margin
        )
        
        if success:
            print("=== ジェットカット処理完了 ===")
        else:
            print("=== ジェットカット処理失敗 ===")
    
    except Exception as e:
        print(f"処理中にエラーが発生しました: {str(e)}")
        print("=== ジェットカット処理失敗 ===")
        return False
    
    return True


if __name__ == "__main__":
    main()
