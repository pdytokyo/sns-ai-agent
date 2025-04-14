"""
voice_input.py - 音声入力を文字起こしするモジュール

マイク入力または音声ファイルからWhisper APIを使用して文字起こしを行います。
"""

import os
import sys
import tempfile
from pathlib import Path
import openai
from openai import OpenAI
import wave

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_api_key, OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

class VoiceInput:
    def __init__(self, api_key=None):
        """
        音声入力クラスの初期化
        
        Args:
            api_key (str, optional): OpenAI APIキー。指定しない場合は環境変数から取得。
        """
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("APIキーが設定されていません。.envファイルにOPENAI_API_KEYを設定してください。")
    
    def close(self):
        """
        オーディオリソースを解放
        """
        pass
    def transcribe_from_file(self, audio_path):
        """
        音声ファイルから文字起こし
        
        Args:
            audio_path (str): 音声ファイルのパス
            
        Returns:
            str: 文字起こし結果
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"ファイルが見つかりません: {audio_path}")
        
        try:
            print(f"文字起こし中: {audio_path}")
            
            with open(audio_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja"
                )
            
            return response.text
        
        except Exception as e:
            print(f"文字起こし中にエラーが発生しました: {str(e)}")
            raise
    
    def transcribe_from_microphone(self, seconds=10):
        """
        マイクから直接録音して文字起こし - 非推奨
        
        このメソッドは後方互換性のために残されていますが、
        ブラウザ側で録音を行い、transcribe_from_fileを使用することを推奨します。
        
        Args:
            seconds (int): 録音する秒数
            
        Returns:
            str: 文字起こし結果
        """
        raise NotImplementedError(
            "このメソッドは非推奨です。ブラウザ側で録音を行い、"
            "transcribe_from_fileメソッドを使用してください。"
        )

def cli_interface():
    """
    コマンドライン用のインターフェース
    """
    try:
        voice_input = VoiceInput()
        
        print("音声編集アシスタント - 音声入力モード")
        print("1. マイクから録音")
        print("2. 音声ファイルから文字起こし")
        choice = input("選択してください (1/2): ")
        
        if choice == "1":
            seconds = int(input("録音する秒数を入力してください (デフォルト: 10): ") or "10")
            transcript = voice_input.transcribe_from_microphone(seconds)
        elif choice == "2":
            audio_path = input("音声ファイルのパスを入力してください: ")
            transcript = voice_input.transcribe_from_file(audio_path)
        else:
            print("無効な選択です。")
            return
        
        print("\n文字起こし結果:")
        print(transcript)
        
        voice_input.close()
        return transcript
    
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return None

if __name__ == "__main__":
    cli_interface()
