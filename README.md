## Sherpath Backend (FastAPI)

本リポジトリは「リアルタイム入力分析機能」を備えた Sherpath のバックエンド（FastAPI）です。企画テキストと添付資料（.docx/.xlsx）から不足情報を提示し、5段階の完成度を返します。Azure Cache for Redis によるキャッシュに対応しています。

### 主なエンドポイント
- POST `/api/analyze`
  - リクエスト: `{ text: string, docText?: string }`
  - レスポンス: `{ completeness: 1-5, suggestions: string[], confidence: number }`
  - 概要: 入力テキストと抽出テキストを統合して、ルール＋AIのハイブリッドで評価します。

- POST `/api/extract_text`
  - フォーム: `files[]`（.docx/.xlsx、最大3ファイル、各10MB）
  - レスポンス: `{ extractedText: string, files: [{ name: string, bytes: number }] }`
  - 概要: Word/Excel のテキスト抽出（OCRは不使用）

- POST `/api/analytics`
  - 概要: 相談内容から論点・質問・相談先を提示（将来のRAG強化も想定）

### 仕組み（要点）
- ルールベース判定（`app/utils/rule_analyzer.py`）
  - 商品/ターゲット/予算/スケジュール/目的/市場 の6分類のキーワードで即時評価
- AI判定（`app/services/analysis_service.py`）
  - OpenAI APIで構造化提案を生成し、ルール結果と統合
- スコアリング（5段階）
  - 0–1スコアへ正規化し、しきい値で 1–5 にマッピング
- キャッシュ
  - キー: `sha256(text + "\n\n" + docText)`、TTL=1時間
  - バックエンド: Azure Cache for Redis（`redis.asyncio`）

### 環境変数（Azure Redis）
以下のいずれかで設定してください。

1) URLで一括指定（推奨）
- `REDIS_URL=rediss://:<PASSWORD>@<HOST>:6380/0`

2) 個別指定
- `REDIS_HOST=redis-OMU.redis.cache.windows.net`
- `REDIS_PORT=6380`
- `REDIS_DB=0`
- `REDIS_SSL=True`
- `REDIS_PASSWORD=<your password>`

任意: `TOKENIZERS_PARALLELISM=false`（HuggingFaceの並列警告抑止）

### セットアップ
1) Python環境（推奨: プロジェクト専用venv）
```
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

2) 起動
```
uvicorn main:app --reload --port 8000
```

3) 動作チェック
```
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text":"新商品の販促。ターゲットは20代、8月実施、目的は新規獲得、予算1000万。"}'

curl -X POST http://localhost:8000/api/extract_text \
  -F "files[]=@/path/to/plan.docx" -F "files[]=@/path/to/estimation.xlsx"
```

### ディレクトリ構成（概要）
```
app/
  api/
    analysis.py        # /api/analyze, /api/extract_text, /api/analytics
    health.py          # /api/health
  services/
    analysis_service.py    # 正規化・5段階スコア・キャッシュ
    analytics_service.py   # 論点・質問・相談先（RAG想定）
    cache_service.py       # Azure Redis接続（redis.asyncio）
    ocr_service.py         # .docx/.xlsx テキスト抽出
    rag_service.py         # RAG機構の土台
    dummy_data_service.py  # ダミーデータ
  models/
    analysis.py        # Pydanticモデル（Analyze/Extract/Analytics）
  utils/
    rule_analyzer.py   # ルールベース判定
main.py                # FastAPIエントリ
requirements.txt
仕様書.md
```

### よくあるエラーと対処
- Redis接続エラー（invalid literal for int() with base 10: 'redis-OMU'）
  - `REDIS_DB` は整数（例: `0`）で指定。`REDIS_URL` 指定も可。
- huggingface_hub の `cached_download` ImportError
  - 依存を同一環境に統一。必要に応じて `sentence-transformers>=2.5.1` などへ更新。


