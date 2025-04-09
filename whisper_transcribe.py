"""
whisper_transcribe.py - 動画の音声を文字起こしして字幕ファイル（SRT）を生成するスクリプト

このスクリプトは指定された動画ファイル（MP4）の音声を抽出し、
OpenAIのWhisper APIを使用して文字起こしを行い、SRT形式の字幕ファイルを生成します。

使用ライブラリ:
- OpenAI Whisper API: 音声の文字起こし
- moviepy: 動画から音声の抽出
"""

import os
import sys
import tempfile
import time
from datetime import timedelta
import openai
from moviepy.editor import VideoFileClip


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
        video.close()
        return True
    except Exception as e:
        print(f"音声抽出中にエラーが発生しました: {str(e)}")
        return False


def transcribe_audio(audio_path, api_key):
    """
    音声ファイルをWhisper APIを使用して文字起こしします。
    
    Args:
        audio_path (str): 音声ファイルのパス
        api_key (str): OpenAI APIキー
        
    Returns:
        dict or None: 文字起こし結果、エラー時はNone
    """
    try:
        print(f"文字起こし中: {audio_path}")
        
        openai.api_key = api_key
        
        with open(audio_path, "rb") as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"  # タイムスタンプ付きの詳細な結果を取得
            )
        
        return response
    except Exception as e:
        print(f"文字起こし中にエラーが発生しました: {str(e)}")
        return None


def format_time(seconds):
    """
    秒数をSRT形式の時間表記（HH:MM:SS,mmm）に変換します。
    
    Args:
        seconds (float): 秒数
        
    Returns:
        str: SRT形式の時間表記
    """
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int(td.microseconds / 1000)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def create_srt_from_response(response, output_srt_path):
    """
    Whisper APIのレスポンスからSRTファイルを作成します。
    
    Args:
        response (dict): Whisper APIのレスポンス
        output_srt_path (str): 出力SRTファイルのパス
        
    Returns:
        bool: 処理が成功したかどうか
    """
    try:
        print(f"SRTファイルを作成中: {output_srt_path}")
        
        os.makedirs(os.path.dirname(output_srt_path), exist_ok=True)
        
        with open(output_srt_path, "w", encoding="utf-8") as srt_file:
            segments = response.get("segments", [])
            
            for i, segment in enumerate(segments):
                start_time = segment.get("start", 0)
                end_time = segment.get("end", 0)
                text = segment.get("text", "").strip()
                
                srt_file.write(f"{i+1}\n")
                srt_file.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
                srt_file.write(f"{text}\n\n")
        
        print(f"SRTファイルの作成が完了しました: {output_srt_path}")
        return True
    except Exception as e:
        print(f"SRTファイル作成中にエラーが発生しました: {str(e)}")
        return False


def get_api_key():
    """
    環境変数からOpenAI APIキーを取得します。
    
    Returns:
        str or None: APIキー、取得できない場合はNone
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("エラー: OPENAI_API_KEYが設定されていません。")
        print("環境変数にOPENAI_API_KEYを設定してください。")
        return None
    return api_key


def main():
    """
    メイン処理を実行します。
    """
    try:
        input_video_path = "videos/input.mp4"
        output_srt_path = "output/subtitles.srt"
        
        print("=== 文字起こし処理開始 ===")
        print(f"入力ファイル: {input_video_path}")
        print(f"出力ファイル: {output_srt_path}")
        print("===========================")
        
        api_key = get_api_key()
        if not api_key:
            return False
        
        if not os.path.exists(input_video_path):
            print(f"エラー: 入力ファイルが見つかりません: {input_video_path}")
            return False
        
        start_time = time.time()
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
            temp_audio_path = temp_audio_file.name
        
        try:
            if not extract_audio(input_video_path, temp_audio_path):
                return False
            
            response = transcribe_audio(temp_audio_path, api_key)
            if not response:
                return False
            
            if not create_srt_from_response(response, output_srt_path):
                return False
            
            elapsed_time = time.time() - start_time
            print(f"総処理時間: {elapsed_time:.2f}秒")
            
            print("=== 文字起こし処理完了 ===")
            return True
            
        finally:
            if os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                    print(f"一時ファイルを削除しました: {temp_audio_path}")
                except Exception as e:
                    print(f"一時ファイルの削除中にエラーが発生しました: {str(e)}")
    
    except Exception as e:
        print(f"処理中にエラーが発生しました: {str(e)}")
        print("=== 文字起こし処理失敗 ===")
        return False
    
    return True


if __name__ == "__main__":
    main()
