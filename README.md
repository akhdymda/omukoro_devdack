# Sherpath API (統合版)

omukoro_devdack_clone と sherpath_backend の機能を統合したバックエンドAPIです。

## 機能

- **企画案分析**: テキストの充実度を分析
- **法令検索**: Cosmos DBを使用したベクトル検索
- **相談提案生成**: OpenAI APIを使用した相談内容分析
- **ヘルスチェック**: 各サービスの状態確認

## 技術スタック

- **FastAPI**: 0.104.1
- **Python**: 3.8+
- **データベース**: Cosmos DB (MongoDB API)
- **キャッシュ**: Redis
- **AI**: OpenAI API

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`env.example` を `.env` にコピーして、必要な値を設定してください：

```bash
cp env.example .env
```

必要な環境変数：
- `OPENAI_API_KEY`: OpenAI APIキー
- `MONGODB_CONNECTION_STRING`: Cosmos DB接続文字列
- `REDIS_URL`: Redis接続URL

### 3. アプリケーションの起動

```bash
python main.py
```

または

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API エンドポイント

### 分析関連
- `POST /api/analyze`: テキストの充実度分析
- `GET /api/analyze/test`: 分析機能のテスト

### 相談関連
- `POST /api/consultations/generate-suggestions`: 相談提案生成
- `GET /api/consultations/{consultation_id}`: 相談詳細取得
- `GET /api/consultations/{consultation_id}/regulations`: 関連法令取得

### システム
- `GET /api/health`: ヘルスチェック
- `GET /`: ルート情報
- `GET /info`: アプリケーション情報

## プロジェクト構造

```
omukoro_devdack_test/
├── app/
│   ├── api/           # APIルーター
│   ├── models/        # Pydanticモデル
│   ├── services/      # ビジネスロジック
│   └── utils/         # ユーティリティ
├── main.py            # メインアプリケーション
├── requirements.txt   # 依存関係
└── README.md         # このファイル
```

## 注意事項

- Cosmos DBへの接続が必要です
- OpenAI APIキーの設定が必要です
- Redisはオプションですが、キャッシュ機能を使用する場合は必要です
