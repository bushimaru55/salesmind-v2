# OpenAI Realtime API (GA版) 実装ガイド

## 概要

SalesMindにOpenAI Realtime API（GA版: `gpt-realtime`）を使用したリアルタイム音声会話機能を実装しました。
ユーザーはテキスト入力とリアルタイム音声会話の2つのモードを切り替えて使用できます。

**重要**: `gpt-4o-realtime-preview-2024-10-01`は非推奨です。本実装はGA版の`gpt-realtime`を使用しています。

## アーキテクチャ

```
ユーザー（ブラウザ）
    ↓
[フロントエンド]
  - RealtimeClient (WebSocket)
  - app-realtime.js (UI制御)
    ↓ WebSocket (wss://)
[Django Channels]
  - RealtimeConsumer (プロキシ)
    ↓ WebSocket
[OpenAI Realtime API]
  - gpt-4o-realtime-preview-2024-10-01
```

## 実装済み機能

### バックエンド

1. **Django Channels統合**
   - `backend/spin/consumers.py` - WebSocketコンシューマー
   - `backend/spin/routing.py` - WebSocketルーティング
   - `backend/salesmind/asgi.py` - ASGI設定

2. **RealtimeConsumer**
   - OpenAI Realtime API（GA版: `gpt-realtime`）へのプロキシ
   - 認証トークンによるユーザー認証
   - 双方向メッセージ転送
   - PCM16音声フォーマット対応
   - セッション履歴への保存（オプション）

3. **Sessionモデル拡張**
   - `realtime_mode` フラグ追加
   - リアルタイム会話セッションの識別

### フロントエンド

1. **RealtimeClient** (`frontend/realtime-client.js`)
   - WebSocket接続管理
   - PCM16形式での音声ストリーミング
   - Web Audio APIによるリアルタイム音声変換
   - イベントハンドリング

2. **UI実装** (`frontend/app-realtime.js`)
   - モード切り替え（テキスト ↔ リアルタイム）
   - 会話開始/停止ボタン
   - ステータス表示
   - リアルタイム文字起こし表示

3. **スタイリング** (`frontend/styles.css`)
   - モード切り替えトグル
   - リアルタイム会話ボタン
   - ステータス表示

### インフラ

1. **Daphne ASGIサーバー**
   - WebSocket対応
   - HTTP/HTTPSとWebSocketの両方をサポート

2. **Nginx設定**
   - WebSocketプロキシ (`/ws/`)
   - アップグレードヘッダー処理

## 使用方法

### ユーザー側

1. **セッション開始**
   - 通常通りSPIN質問を生成してセッションを開始

2. **モード切り替え**
   - チャット画面で「💬 テキスト」または「🎤 リアルタイム会話」を選択

3. **リアルタイム会話**
   - 「会話を開始」ボタンをクリック
   - マイクへのアクセスを許可
   - 話し始めると自動的に音声認識が開始
   - AIの応答がリアルタイムで表示される
   - 「会話を停止」ボタンで終了

4. **テキスト入力**
   - 従来通りテキスト入力または音声録音→変換が可能

### 開発者側

#### WebSocket接続テスト

```javascript
// ブラウザコンソールで実行
const client = new RealtimeClient(authToken, sessionId);

client.onConnected = () => console.log('Connected!');
client.onError = (error) => console.error('Error:', error);
client.onTranscript = (text, role) => console.log(`${role}: ${text}`);

await client.connect();
await client.startAudioStream();
```

#### バックエンドログ確認

```bash
# Daphneサーバーログ
docker compose logs web --tail 50 --follow

# WebSocket接続ログ
docker compose logs web | grep -i "websocket\|realtime"
```

## 設定

### 環境変数

`.env`ファイルに以下を設定：

```bash
# OpenAI API Key（必須）
OPENAI_API_KEY=sk-...

# Django設定
DEBUG=False
ALLOWED_HOSTS=salesmind.mind-bridge.tech
```

### Django Channels設定

`backend/salesmind/settings.py`:

```python
INSTALLED_APPS = [
    "daphne",  # 最初に配置
    "channels",
    # ...
]

ASGI_APPLICATION = "salesmind.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}
```

## トラブルシューティング

### WebSocket接続エラー

**症状**: "WebSocket connection failed"

**原因と対処**:
1. Daphneサーバーが起動していない
   ```bash
   docker compose logs web
   # "Starting Daphne ASGI server..." が表示されるか確認
   ```

2. Nginxの設定エラー
   ```bash
   docker compose logs frontend
   # WebSocketアップグレードエラーを確認
   ```

3. 認証トークンが無効
   - ブラウザコンソールでauthTokenを確認
   - 再ログインを試す

### マイクアクセスエラー

**症状**: "Failed to start audio"

**対処**:
1. ブラウザのマイク許可を確認
2. HTTPSで接続しているか確認（HTTPではマイクアクセス不可）
3. 他のアプリケーションがマイクを使用していないか確認

### OpenAI API エラー

**症状**: "Failed to connect to OpenAI"

**対処**:
1. OPENAI_API_KEYが正しく設定されているか確認
   ```bash
   docker compose exec web env | grep OPENAI_API_KEY
   ```

2. OpenAI APIの利用制限を確認
   - レート制限: 10同時接続/アカウント
   - セッション時間: 最大15分

3. ネットワーク接続を確認

### 音声が認識されない

**症状**: 話しているが文字起こしが表示されない

**対処**:
1. マイクの音量を確認
2. ブラウザコンソールでWebSocketメッセージを確認
3. VAD（Voice Activity Detection）の閾値を調整
   - `realtime-client.js`の`turn_detection.threshold`を変更

## パフォーマンス最適化

### 推奨設定

1. **音声品質**
   - サンプリングレート: 24000Hz
   - フォーマット: PCM16
   - エコーキャンセル: 有効
   - ノイズ抑制: 有効

2. **ネットワーク**
   - 最小帯域幅: 128kbps
   - 推奨帯域幅: 256kbps以上
   - レイテンシ: 100ms以下推奨

3. **サーバー**
   - Daphne workers: CPU数に応じて調整
   - WebSocketタイムアウト: 86400秒（24時間）

## セキュリティ

### 実装済み対策

1. **認証**
   - トークンベース認証（Django Token Authentication）
   - WebSocket接続時にトークン検証

2. **セッション管理**
   - ユーザーごとにセッションを分離
   - 不正なセッションIDは拒否

3. **レート制限**
   - OpenAI側の制限（10同時接続/アカウント）
   - 必要に応じてDjango側でも実装可能

### 推奨事項

1. **本番環境**
   - HTTPS必須
   - WSS（WebSocket Secure）使用
   - CORS設定の厳格化

2. **監視**
   - WebSocket接続数の監視
   - エラーレートの監視
   - OpenAI API使用量の監視

## 今後の拡張

### 実装予定機能

1. **セッション統合**
   - リアルタイム会話の完全なセッション履歴保存
   - 温度スコアのリアルタイム更新

2. **Redis Channel Layer**
   - 複数サーバー対応
   - スケーラビリティ向上

3. **音声再生**
   - AIの音声応答を再生
   - テキスト読み上げ

4. **会話分析**
   - リアルタイム感情分析
   - SPIN段階の自動判定

## モデル情報

### 使用モデル
- **gpt-realtime**: GA版（本番推奨）
- **gpt-realtime-mini**: 軽量版（コスト重視）

### 非推奨モデル
- ~~gpt-4o-realtime-preview-2024-10-01~~: プレビュー版（廃止予定）

## 参考資料

- [OpenAI Realtime API ガイド](https://platform.openai.com/docs/guides/realtime)
- [gpt-realtime モデルページ](https://platform.openai.com/docs/models/gpt-realtime)
- [OpenAI モデル一覧](https://platform.openai.com/docs/models)
- [Django Channels Documentation](https://channels.readthedocs.io/)
- [Daphne Documentation](https://github.com/django/daphne)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)

## サポート

問題が発生した場合は、以下の情報を収集してください：

1. ブラウザコンソールのエラーログ
2. Djangoサーバーログ（`docker compose logs web`）
3. Nginxログ（`docker compose logs frontend`）
4. 使用環境（ブラウザ、OS、ネットワーク）

