# 音声入力機能（Speech-to-Text）仕様書

## 概要
チャット画面でユーザーの音声入力をサポートし、GCP Speech-to-Text APIを使用して音声をテキストに変換する機能。

## 目的
- より自然な商談練習を可能にする
- タイピングの負担を軽減し、会話に集中できるようにする
- 実践的な商談シミュレーションを提供する

## 技術スタック
- **フロントエンド**: Web Speech API（MediaRecorder API）を使用して音声を録音
- **バックエンド**: GCP Speech-to-Text APIを使用して音声をテキストに変換
- **認証**: GCPサービスアカウントキーを使用

## 機能仕様

### 1. 音声録音機能
- **録音開始**: マイクボタンをクリックして録音を開始
- **録音停止**: 再度マイクボタンをクリックして録音を停止
- **録音中の視覚的フィードバック**: 録音中はボタンが点滅または色が変わる
- **録音時間の表示**: 録音中の経過時間を表示

### 2. 音声送信・変換
- **音声データの送信**: 録音した音声データをバックエンドに送信
- **GCP Speech-to-Text API呼び出し**: バックエンドでGCP APIを呼び出してテキストに変換
- **変換結果の取得**: 変換されたテキストをフロントエンドに返す

### 3. テキスト反映
- **入力欄への自動入力**: 変換されたテキストをチャット入力欄に自動入力
- **編集可能**: ユーザーは変換結果を編集してから送信可能
- **送信**: 通常のテキスト入力と同様に送信ボタンで送信

## API仕様

### エンドポイント
```
POST /api/speech/transcribe/
```

### リクエスト
- **認証**: Token認証必須
- **Content-Type**: `multipart/form-data`
- **Body**:
  - `audio`: 音声ファイル（WAV、MP3、FLACなど）
  - `language_code`: 言語コード（デフォルト: `ja-JP`）

### レスポンス
```json
{
  "text": "変換されたテキスト",
  "confidence": 0.95
}
```

### エラーレスポンス
```json
{
  "error": "エラーメッセージ",
  "detail": "詳細なエラー情報"
}
```

## GCP Speech-to-Text API設定手順

### 1. GCPプロジェクトの作成・選択
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. プロジェクトを選択または新規作成
3. プロジェクトIDをメモしておく

### 2. Speech-to-Text APIの有効化
1. Cloud Consoleで「APIとサービス」→「ライブラリ」に移動
2. 「Cloud Speech-to-Text API」を検索
3. APIを選択して「有効にする」をクリック

### 3. サービスアカウントの作成
1. 「IAMと管理」→「サービスアカウント」に移動
2. 「サービスアカウントを作成」をクリック
3. 以下の情報を入力：
   - **サービスアカウント名**: `speech-to-text-service`（任意）
   - **サービスアカウントID**: 自動生成される
   - **説明**: 「Speech-to-Text API用サービスアカウント」
4. 「作成して続行」をクリック
5. **ロール**: 「Cloud Speech Client」を選択（または「Cloud Speech-to-Text API User」）
6. 「続行」→「完了」をクリック

### 4. サービスアカウントキーの作成
1. 作成したサービスアカウントをクリック
2. 「キー」タブを選択
3. 「キーを追加」→「新しいキーを作成」を選択
4. **キーのタイプ**: JSONを選択
5. 「作成」をクリック
6. JSONファイルがダウンロードされる（例: `salesmind-speech-to-text-xxxxx.json`）

### 5. 環境変数の設定

#### ローカル開発環境の場合
1. ダウンロードしたJSONファイルをプロジェクトルートに配置（例: `gcp-credentials.json`）
2. `.env`ファイルに以下を追加：
```env
GOOGLE_APPLICATION_CREDENTIALS=./gcp-credentials.json
```

#### Docker環境の場合
1. JSONファイルを`backend/`ディレクトリに配置（例: `backend/gcp-credentials.json`）
2. `docker-compose.yml`の`web`サービスに以下を追加：
```yaml
volumes:
  - ./backend:/app
  - ./backend/gcp-credentials.json:/app/gcp-credentials.json:ro
environment:
  - GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json
```
3. `.env`ファイルに以下を追加：
```env
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json
```

### 6. 認証方法の選択
既存の実装（`speech_to_text.py`）は以下の2つの方法をサポート：

#### 方法1: サービスアカウントキーファイル（推奨）
- `GOOGLE_APPLICATION_CREDENTIALS`環境変数にJSONファイルのパスを設定
- 上記の手順5で設定済み

#### 方法2: デフォルト認証（GCP環境やgcloud認証済みの場合）
- GCP環境で実行している場合、または`gcloud auth application-default login`を実行済みの場合
- 環境変数の設定は不要

### 7. 動作確認
1. サーバーを起動
2. 以下のエンドポイントに音声ファイルをPOST：
   - URL: `http://localhost:8000/api/speech/transcribe/`
   - Method: POST
   - Headers: `Authorization: Token <your-token>`
   - Body: `multipart/form-data`
     - `audio`: 音声ファイル（WAV、MP3、FLACなど）
     - `language_code`: `ja-JP`（オプション）

### セキュリティ考慮事項（GCP設定）
1. **JSONファイルの管理**:
   - `.gitignore`に`*.json`（サービスアカウントキー）を追加
   - 本番環境では環境変数やシークレット管理サービスを使用
2. **権限の最小化**:
   - サービスアカウントには必要最小限の権限のみを付与
3. **キーのローテーション**:
   - 定期的にキーを更新することを推奨

### トラブルシューティング（GCP設定）
- **認証エラー**: `GOOGLE_APPLICATION_CREDENTIALS`のパスが正しいか確認
- **API有効化エラー**: Speech-to-Text APIが有効になっているか確認
- **権限エラー**: サービスアカウントに適切なロールが付与されているか確認

## 実装詳細

### バックエンド実装

#### 1. 依存関係の追加
- `google-cloud-speech` を `requirements.txt` に追加（既に追加済み）

#### 2. 環境変数
- `GOOGLE_APPLICATION_CREDENTIALS`: GCPサービスアカウントキーのパス
- または、GCPのデフォルト認証を使用

#### 3. エンドポイント実装
- `backend/spin/views.py` に `transcribe_speech` 関数を追加
- `backend/spin/urls.py` にルートを追加

#### 4. サービス実装
- `backend/spin/services/speech_to_text.py` を作成
- GCP Speech-to-Text APIクライアントの初期化
- 音声ファイルの変換処理

### フロントエンド実装

#### 1. UI要素の追加
- チャット入力欄にマイクボタンを追加
- 録音中の視覚的フィードバック（アニメーション、色変更）
- 録音時間の表示

#### 2. 音声録音機能
- `app.js` に音声録音関数を追加
- MediaRecorder APIを使用して音声を録音
- 録音データをBlob形式で保存

#### 3. 音声送信機能
- 録音停止後、音声データをFormDataでバックエンドに送信
- レスポンスからテキストを取得して入力欄に反映

#### 4. エラーハンドリング
- マイクアクセス拒否時のエラー表示
- 音声変換失敗時のエラー表示
- ネットワークエラー時のエラー表示

## セキュリティ考慮事項

### 1. 認証
- 音声変換APIは認証必須
- トークンベースの認証を使用

### 2. ファイルサイズ制限
- 音声ファイルのサイズ制限を設定（例: 10MB）
- 録音時間の制限（例: 60秒）

### 3. レート制限
- ユーザーごとのリクエスト回数制限
- 過度なAPI呼び出しを防止

## エラーハンドリング

### 1. マイクアクセス拒否
- ユーザーにマイクアクセス許可を促すメッセージを表示
- ブラウザの設定方法を案内

### 2. 音声変換失敗
- エラーメッセージを表示
- 再試行を促す

### 3. ネットワークエラー
- 接続エラーメッセージを表示
- オフライン時の処理

## ブラウザ対応

### サポートブラウザ
- Chrome/Edge（推奨）
- Firefox
- Safari（制限あり）

### フォールバック
- 音声入力が利用できない場合は、マイクボタンを非表示
- テキスト入力のみで利用可能

## 今後の拡張機能

### 1. リアルタイム音声認識
- Web Speech APIの`SpeechRecognition`を使用してリアルタイム変換
- より自然な会話体験を提供

### 2. 話し方の分析
- 話す速度、間、トーンの分析
- 営業スキルの評価に活用

### 3. 多言語対応
- 英語、中国語など他の言語にも対応

## 実装日
2025-12-20

## 更新履歴
- 2025-12-20: 初版作成
- 2025-01-XX: GCP Speech-to-Text API設定手順を追加

