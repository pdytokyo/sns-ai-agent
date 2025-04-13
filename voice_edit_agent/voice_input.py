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
import pyaudio
import numpy as np

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
        
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        self.audio = pyaudio.PyAudio()
    
    def record_audio(self, seconds=10, output_path=None):
        """
        マイクから音声を録音
        
        Args:
            seconds (int): 録音する秒数
            output_path (str, optional): 出力ファイルのパス。指定しない場合は一時ファイル。
            
        Returns:
            str: 録音した音声ファイルのパス
        """
        print(f"{seconds}秒間の録音を開始します。話してください...")
        
        if not output_path:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                output_path = temp_file.name
        
        stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        frames = []
        for i in range(0, int(self.rate / self.chunk * seconds)):
            data = stream.read(self.chunk)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        
        wf = wave.open(output_path, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.audio.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print(f"録音が完了しました: {output_path}")
        return output_path
    
    def close(self):
        """
        オーディオリソースを解放
        """
        self.audio.terminate()
    
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
        マイクから直接録音して文字起こし
        
        Args:
            seconds (int): 録音する秒数
            
        Returns:
            str: 文字起こし結果
        """
        try:
            audio_path = self.record_audio(seconds)
            transcription = self.transcribe_from_file(audio_path)
            
            os.remove(audio_path)
            
            return transcription
        
        except Exception as e:
            print(f"マイク録音・文字起こし中にエラーが発生しました: {str(e)}")
            raise

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
