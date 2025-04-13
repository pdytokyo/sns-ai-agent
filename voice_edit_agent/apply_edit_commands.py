"""
apply_edit_commands.py - 編集コマンドを動画に適用するモジュール

JSONフォーマットの編集コマンドを受け取り、既存の編集モジュールを使用して
動画に編集を適用します。
"""

import os
import sys
import json
import sqlite3
import tempfile
import uuid
from pathlib import Path
from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH
from subtitle_generator import generate_subtitles
from bgm_integrator import add_bgm_to_video

class EditCommandProcessor:
    def __init__(self, video_path=None):
        """
        編集コマンドプロセッサの初期化
        
        Args:
            video_path (str, optional): 編集する動画のパス
        """
        self.video_path = video_path
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def set_video_path(self, video_path):
        """
        編集する動画のパスを設定
        
        Args:
            video_path (str): 動画ファイルのパス
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")
        
        self.video_path = video_path
    
    def get_video_metadata(self):
        """
        動画のメタデータを取得
        
        Returns:
            dict: 動画のメタデータ（長さ、解像度など）
        """
        if not self.video_path or not os.path.exists(self.video_path):
            raise ValueError("有効な動画パスが設定されていません")
        
        try:
            with VideoFileClip(self.video_path) as clip:
                return {
                    "duration": clip.duration,
                    "resolution": f"{clip.w}x{clip.h}",
                    "fps": clip.fps,
                    "audio": clip.audio is not None
                }
        except Exception as e:
            raise Exception(f"動画メタデータの取得中にエラーが発生しました: {str(e)}")
    
    def apply_cut(self, video_clip, start, end):
        """
        動画の一部をカット（削除）
        
        Args:
            video_clip (VideoFileClip): 元の動画クリップ
            start (float): カット開始時間（秒）
            end (float): カット終了時間（秒）
            
        Returns:
            VideoFileClip: 編集後の動画クリップ
        """
        if start >= end or start < 0 or end > video_clip.duration:
            print(f"警告: 無効なカット範囲 ({start}s-{end}s), 動画の長さ: {video_clip.duration}s")
            return video_clip
        
        if start > 0 and end < video_clip.duration:
            part1 = video_clip.subclip(0, start)
            part2 = video_clip.subclip(end, video_clip.duration)
            return concatenate_videoclips([part1, part2])
        elif start > 0:
            return video_clip.subclip(0, start)
        elif end < video_clip.duration:
            return video_clip.subclip(end, video_clip.duration)
        else:
            print("警告: 動画全体がカットされます")
            return None
    
    def apply_trim(self, video_clip, start, end):
        """
        指定した部分だけを残して他をカット
        
        Args:
            video_clip (VideoFileClip): 元の動画クリップ
            start (float): 残す開始時間（秒）
            end (float): 残す終了時間（秒）
            
        Returns:
            VideoFileClip: 編集後の動画クリップ
        """
        if start >= end or start < 0 or end > video_clip.duration:
            print(f"警告: 無効なトリム範囲 ({start}s-{end}s), 動画の長さ: {video_clip.duration}s")
            return video_clip
        
        return video_clip.subclip(start, end)
    
    def apply_subtitle(self, video_clip, text, start, end):
        """
        テロップ（字幕）を追加
        
        Args:
            video_clip (VideoFileClip): 元の動画クリップ
            text (str): テロップのテキスト
            start (float): 表示開始時間（秒）
            end (float): 表示終了時間（秒）
            
        Returns:
            VideoFileClip: 編集後の動画クリップ
        """
        if start >= end or start < 0 or end > video_clip.duration:
            print(f"警告: 無効な字幕範囲 ({start}s-{end}s), 動画の長さ: {video_clip.duration}s")
            return video_clip
        
        txt_clip = TextClip(
            text,
            fontsize=70,
            color='white',
            stroke_color='black',
            stroke_width=2,
            font='Arial-Bold',
            method='caption',
            size=(video_clip.w * 0.8, None)
        )
        
        txt_clip = txt_clip.set_position(('center', 'bottom')).set_start(start).set_end(end)
        
        return CompositeVideoClip([video_clip, txt_clip])
    
    def apply_speed(self, video_clip, start, end, rate):
        """
        動画の速度を変更
        
        Args:
            video_clip (VideoFileClip): 元の動画クリップ
            start (float): 速度変更開始時間（秒）
            end (float): 速度変更終了時間（秒）
            rate (float): 速度倍率
            
        Returns:
            VideoFileClip: 編集後の動画クリップ
        """
        if start >= end or start < 0 or end > video_clip.duration:
            print(f"警告: 無効な速度変更範囲 ({start}s-{end}s), 動画の長さ: {video_clip.duration}s")
            return video_clip
        
        part_to_speed = video_clip.subclip(start, end)
        
        speed_part = part_to_speed.speedx(rate)
        
        if start > 0 and end < video_clip.duration:
            part1 = video_clip.subclip(0, start)
            part3 = video_clip.subclip(end, video_clip.duration)
            return concatenate_videoclips([part1, speed_part, part3])
        elif start > 0:
            part1 = video_clip.subclip(0, start)
            return concatenate_videoclips([part1, speed_part])
        elif end < video_clip.duration:
            part3 = video_clip.subclip(end, video_clip.duration)
            return concatenate_videoclips([speed_part, part3])
        else:
            return speed_part
    
    def process_commands(self, edit_commands, video_path=None, client_id=None, script_id=None):
        """
        編集コマンドを処理して動画に適用
        
        Args:
            edit_commands (dict): 編集コマンドJSON
            video_path (str, optional): 動画ファイルのパス。指定しない場合はself.video_pathを使用
            client_id (int, optional): クライアントID
            script_id (int, optional): 台本ID
            
        Returns:
            str: 編集後の動画ファイルのパス
        """
        video_path_to_use = video_path or self.video_path
        
        if not video_path_to_use or not os.path.exists(video_path_to_use):
            raise ValueError("有効な動画パスが設定されていません")
        
        if "edits" not in edit_commands or not edit_commands["edits"]:
            print("警告: 有効な編集コマンドがありません")
            return video_path_to_use
        
        try:
            video_clip = VideoFileClip(video_path_to_use)
            
            bgm_commands = [cmd for cmd in edit_commands["edits"] if cmd["type"] == "bgm_replace"]
            other_commands = [cmd for cmd in edit_commands["edits"] if cmd["type"] != "bgm_replace"]
            
            for cmd in other_commands:
                cmd_type = cmd["type"]
                
                if cmd_type == "cut":
                    video_clip = self.apply_cut(video_clip, cmd["start"], cmd["end"])
                    if video_clip is None:
                        raise ValueError("カット後に動画が残りませんでした")
                
                elif cmd_type == "trim":
                    video_clip = self.apply_trim(video_clip, cmd["start"], cmd["end"])
                
                elif cmd_type == "subtitle":
                    video_clip = self.apply_subtitle(video_clip, cmd["text"], cmd["start"], cmd["end"])
                
                elif cmd_type == "speed":
                    video_clip = self.apply_speed(video_clip, cmd["start"], cmd["end"], cmd["rate"])
            
            temp_output_path = os.path.join(self.output_dir, f"temp_{uuid.uuid4().hex}.mp4")
            video_clip.write_videofile(
                temp_output_path,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile="temp-audio.m4a",
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            video_clip.close()
            
            final_output_path = os.path.join(self.output_dir, f"edited_{uuid.uuid4().hex}.mp4")
            
            if bgm_commands:
                bgm_cmd = bgm_commands[-1]
                mood = bgm_cmd.get("mood", "uplifting")
                
                bgm_id = self.get_bgm_by_mood(mood)
                
                if bgm_id:
                    final_output_path = add_bgm_to_video(temp_output_path, self.get_bgm_path(bgm_id), 0.5, self.output_dir)
                    
                    if os.path.exists(temp_output_path):
                        os.remove(temp_output_path)
                else:
                    final_output_path = temp_output_path
            else:
                final_output_path = temp_output_path
            
            if client_id is not None:
                self.save_edit_command(edit_commands, video_path_to_use, final_output_path, client_id, script_id)
                
            return final_output_path
        
        except Exception as e:
            raise Exception(f"編集コマンド処理中にエラーが発生しました: {str(e)}")
    
    def get_bgm_by_mood(self, mood):
        """
        指定したムードのBGMを取得
        
        Args:
            mood (str): BGMのムード
            
        Returns:
            int: BGMのID
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM copyright_free_audio WHERE mood LIKE ? ORDER BY RANDOM() LIMIT 1",
            (f"%{mood}%",)
        )
        result = cursor.fetchone()
        
        conn.close()
        
        return result[0] if result else None
    
    def get_bgm_path(self, bgm_id):
        """
        BGMのファイルパスを取得
        
        Args:
            bgm_id (int): BGMのID
            
        Returns:
            str: BGMのファイルパス
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT file_path FROM copyright_free_audio WHERE id = ?",
            (bgm_id,)
        )
        result = cursor.fetchone()
        
        conn.close()
        
        if not result:
            raise ValueError(f"BGMが見つかりません: ID {bgm_id}")
        
        return result[0]
    
    def save_edit_command(self, command_json, video_path, result_path, client_id=None, script_id=None):
        """
        編集コマンドをデータベースに保存
        
        Args:
            command_json (dict): 編集コマンドJSON
            video_path (str): 元の動画パス
            result_path (str): 編集結果の動画パス
            client_id (int, optional): クライアントID
            script_id (int, optional): 台本ID
            
        Returns:
            int: 保存された編集コマンドのID
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO edit_commands (client_id, script_id, command_json, video_path, result_path) VALUES (?, ?, ?, ?, ?)",
            (client_id, script_id, json.dumps(command_json), video_path, result_path)
        )
        
        command_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return command_id

def cli_interface():
    """
    コマンドライン用のインターフェース
    """
    try:
        processor = EditCommandProcessor()
        
        print("音声編集アシスタント - 編集コマンド適用モード")
        
        video_path = input("編集する動画ファイルのパスを入力してください: ")
        processor.set_video_path(video_path)
        
        metadata = processor.get_video_metadata()
        print(f"\n動画情報:")
        print(f"長さ: {metadata['duration']}秒")
        print(f"解像度: {metadata['resolution']}")
        print(f"FPS: {metadata['fps']}")
        print(f"音声: {'あり' if metadata['audio'] else 'なし'}")
        
        print("\n編集コマンドJSONを入力してください（例: {\"edits\": [{\"type\": \"cut\", \"start\": 0, \"end\": 5}]}）")
        print("または、JSONファイルのパスを入力してください:")
        
        command_input = input("> ")
        
        if os.path.exists(command_input):
            with open(command_input, 'r', encoding='utf-8') as f:
                edit_commands = json.load(f)
        else:
            edit_commands = json.loads(command_input)
        
        print("\n編集を開始します...")
        result_path = processor.process_commands(edit_commands)
        
        print(f"\n編集が完了しました: {result_path}")
        
        save_to_db = input("\nデータベースに保存しますか？ (y/n): ").lower() == 'y'
        
        if save_to_db:
            client_id = input("クライアントID（省略可）: ")
            script_id = input("台本ID（省略可）: ")
            
            client_id = int(client_id) if client_id else None
            script_id = int(script_id) if script_id else None
            
            command_id = processor.save_edit_command(edit_commands, processor.video_path, result_path, client_id, script_id)
            print(f"編集コマンドをデータベースに保存しました: ID {command_id}")
        
        return result_path
    
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return None

if __name__ == "__main__":
    cli_interface()
