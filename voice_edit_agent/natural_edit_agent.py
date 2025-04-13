"""
natural_edit_agent.py - 自然言語を編集コマンドに変換するモジュール

ユーザーの自然言語指示をGPT-4 APIを使用して編集コマンドJSON形式に変換します。
"""

import os
import sys
import json
from openai import OpenAI

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_api_key, OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

class NaturalEditAgent:
    def __init__(self, api_key=None):
        """
        自然言語編集エージェントの初期化
        
        Args:
            api_key (str, optional): OpenAI APIキー。指定しない場合は環境変数から取得。
        """
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("APIキーが設定されていません。.envファイルにOPENAI_API_KEYを設定してください。")
    
    def convert_to_edit_commands(self, natural_language, video_metadata=None):
        """
        自然言語指示を編集コマンドJSONに変換
        
        Args:
            natural_language (str): ユーザーからの自然言語指示
            video_metadata (dict, optional): 動画のメタデータ（長さ、解像度など）
            
        Returns:
            dict: 編集コマンドJSON
        """
        system_message = """
        あなたは動画編集AIアシスタントです。ユーザーの自然言語による編集指示を、正確なJSONフォーマットの編集コマンドに変換します。
        
        以下の編集タイプをサポートしています:
        1. cut: 動画の一部をカット（削除）
        2. subtitle: 特定の時間にテロップ（字幕）を追加
        3. bgm_replace: BGMを置き換え（指定されたムードの音楽を使用）
        4. speed: 速度変更（特定部分の再生速度を変更）
        5. trim: 指定した部分だけを残して他をカット
        
        JSON形式:
        {
          "edits": [
            { "type": "cut", "start": 開始秒数, "end": 終了秒数 },
            { "type": "subtitle", "text": "テキスト", "start": 開始秒数, "end": 終了秒数 },
            { "type": "bgm_replace", "mood": "ムード" },
            { "type": "speed", "start": 開始秒数, "end": 終了秒数, "rate": 倍率 },
            { "type": "trim", "start": 開始秒数, "end": 終了秒数 }
          ]
        }
        
        時間は秒単位の数値で指定してください。速度の倍率は0.5（半分速度）から2.0（倍速）の範囲が推奨です。
        BGMのムードは "uplifting", "dramatic", "peaceful", "energetic", "sad" などが利用可能です。
        
        指示が曖昧な場合は最適な解釈を行い、明確なJSONを生成してください。
        動画全体に対する指示（「全体的に明るくする」など）はサポートされていないため、代替案を提案してください。
        """
        
        user_message = natural_language
        
        if video_metadata:
            user_message += f"\n\n動画情報:\n長さ: {video_metadata.get('duration', '不明')}秒\n解像度: {video_metadata.get('resolution', '不明')}"
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=1000,
                temperature=0.2
            )
            
            response_text = response.choices[0].message.content
            
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    edit_commands = json.loads(json_str)
                    
                    if "edits" not in edit_commands:
                        edit_commands = {"edits": []}
                    
                    return edit_commands
                else:
                    raise ValueError("応答からJSON形式を抽出できませんでした")
            
            except json.JSONDecodeError:
                return {"edits": [], "error": "JSONパースエラー", "raw_response": response_text}
        
        except Exception as e:
            print(f"編集コマンド生成中にエラーが発生しました: {str(e)}")
            return {"edits": [], "error": str(e)}
    
    def validate_commands(self, edit_commands, video_duration=None):
        """
        編集コマンドを検証し、問題があれば修正
        
        Args:
            edit_commands (dict): 編集コマンドJSON
            video_duration (float, optional): 動画の長さ（秒）
            
        Returns:
            dict: 検証・修正された編集コマンド
        """
        if "edits" not in edit_commands:
            return {"edits": [], "error": "無効な編集コマンド形式"}
        
        validated_edits = []
        
        for edit in edit_commands["edits"]:
            if "type" not in edit:
                continue
            
            edit_type = edit["type"]
            validated_edit = {"type": edit_type}
            
            if edit_type in ["cut", "subtitle", "speed", "trim"]:
                start = float(edit.get("start", 0))
                end = float(edit.get("end", video_duration or 3600))
                
                if video_duration:
                    start = max(0, min(start, video_duration))
                    end = max(0, min(end, video_duration))
                
                if start >= end:
                    continue
                
                validated_edit["start"] = start
                validated_edit["end"] = end
                
                if edit_type == "subtitle":
                    if "text" not in edit:
                        continue
                    validated_edit["text"] = edit["text"]
                
                elif edit_type == "speed":
                    rate = float(edit.get("rate", 1.0))
                    rate = max(0.5, min(rate, 2.0))
                    validated_edit["rate"] = rate
            
            elif edit_type == "bgm_replace":
                if "mood" not in edit:
                    continue
                validated_edit["mood"] = edit["mood"]
            
            else:
                continue
            
            validated_edits.append(validated_edit)
        
        return {"edits": validated_edits}

def cli_interface():
    """
    コマンドライン用のインターフェース
    """
    try:
        agent = NaturalEditAgent()
        
        print("音声編集アシスタント - 編集コマンド変換モード")
        print("自然言語で編集指示を入力してください（例: 「最初の5秒をカットして、10秒から15秒の間に「見てください！」というテロップを入れて」）")
        
        natural_language = input("> ")
        
        video_duration = input("動画の長さ（秒）を入力してください（省略可）: ")
        video_metadata = {"duration": float(video_duration)} if video_duration else None
        
        edit_commands = agent.convert_to_edit_commands(natural_language, video_metadata)
        validated_commands = agent.validate_commands(edit_commands, float(video_duration) if video_duration else None)
        
        print("\n生成された編集コマンド:")
        print(json.dumps(validated_commands, indent=2, ensure_ascii=False))
        
        return validated_commands
    
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return None

if __name__ == "__main__":
    cli_interface()
