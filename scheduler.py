import os
import time
import schedule
import threading
from datetime import datetime
from trend_collector import collect_all_trends

def job_collect_trends():
    """トレンド収集ジョブ"""
    print(f"[{datetime.now()}] トレンド収集ジョブを実行します...")
    trends = collect_all_trends()
    print(f"収集完了: Google({len(trends['google'])}), YouTube({len(trends['youtube'])}), TikTok({len(trends['tiktok'])})")
    return trends

def run_scheduler():
    """スケジューラーの実行"""
    schedule.every().monday.at("09:00").do(job_collect_trends)
    
    
    job_collect_trends()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1分ごとにスケジュールをチェック

def start_scheduler_thread():
    """スケジューラーを別スレッドで起動"""
    thread = threading.Thread(target=run_scheduler)
    thread.daemon = True  # メインスレッドが終了したら終了
    thread.start()
    return thread

if __name__ == "__main__":
    print("トレンド収集スケジューラーを開始します...")
    run_scheduler()
