# SNS AI Agent

SNS AI Agentは、ソーシャルネットワークサービス（SNS）の利用戦略に関する研究と提案生成システムです。

## Webプロトタイプ

このリポジトリには、クライアント情報管理、ファイルアップロード、AI生成プロフィールと台本機能を備えたWebインターフェースのプロトタイプが含まれています。

### 機能

- ターゲット属性（年齢、性別、興味関心）・運用目的・プラットフォーム（YouTube、Instagram、TikTok）の選択
- 動画・テキスト・PDFのアップロード（ファイルをSQLiteにパスとして保存）
- クライアント情報・選択結果をSQLiteに保存する機能
- SQLiteのデータからアカウント名とプロフィール欄をAIが自動生成し、クライアントが微調整・保存できるUI
- 台本を複数生成し、クライアントが選択・微調整できるUI（台本生成回数は無制限）

### 技術スタック

- FastAPI
- SQLite
- OpenAI API（GPT-4oモデル）

### 実行方法

1. 必要なパッケージをインストール: `pip install -r requirements.txt`
2. .envファイルにOpenAI APIキーを設定: `OPENAI_API_KEY=your_api_key`
3. アプリケーションを起動: `python -m app.main`
4. ブラウザで http://localhost:8000 にアクセス
