# リアルタイムモード不整合修正 - 検証手順

## ✅ 実施した修正

### 1. SessionSerializer の修正
- **ファイル**: `backend/spin/serializers.py`
- **変更内容**:
  - `fields` に `'realtime_mode'` を追加
  - `read_only_fields` に `'realtime_mode'` を追加
- **効果**: API経由で `realtime_mode` の状態を取得可能に

### 2. WebSocket Consumer の修正
- **ファイル**: `backend/spin/consumers.py`
- **変更内容**:
  - `connect()`: WebSocket接続時に `session.realtime_mode = True` に更新
  - `disconnect()`: WebSocket切断時に `session.realtime_mode = False` に更新
  - `update_session_realtime_mode()`: セッション状態を更新する新メソッドを追加
- **効果**: リアルタイムモードの状態がバックエンドで正確に管理される

---

## 🧪 検証手順

### テスト 1: セッション作成時の初期値確認

1. **セッションを作成**:
   ```bash
   curl -X POST https://salesmind.mind-bridge.tech/api/session/start/ \
     -H "Authorization: Token YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "industry": "IT",
       "value_proposition": "クラウドサービス"
     }'
   ```

2. **期待される結果**:
   ```json
   {
     "id": "...",
     "realtime_mode": false,  // ← 初期値は false
     "mode": "simple",
     "industry": "IT",
     ...
   }
   ```

---

### テスト 2: WebSocket接続時の状態更新確認

1. **ブラウザで以下を実行**:
   - ログイン
   - セッションを開始
   - 「🎤 リアルタイム会話」モードを選択
   - 「会話を開始」をクリック

2. **バックエンドログを確認**:
   ```bash
   docker compose logs web --tail 50 | grep "realtime_mode"
   ```

3. **期待されるログ**:
   ```
   ✅ Session XXXX realtime_mode updated to True
   ```

4. **セッション情報をAPI経由で確認**:
   ```bash
   curl -X GET https://salesmind.mind-bridge.tech/api/session/SESSION_ID/ \
     -H "Authorization: Token YOUR_TOKEN"
   ```

5. **期待される結果**:
   ```json
   {
     "id": "SESSION_ID",
     "realtime_mode": true,  // ← WebSocket接続中は true
     ...
   }
   ```

---

### テスト 3: WebSocket切断時の状態更新確認

1. **ブラウザで「会話を停止」をクリック**

2. **バックエンドログを確認**:
   ```bash
   docker compose logs web --tail 50 | grep "realtime_mode"
   ```

3. **期待されるログ**:
   ```
   ✅ Session XXXX realtime_mode updated to False
   ```

4. **セッション情報をAPI経由で確認**:
   ```bash
   curl -X GET https://salesmind.mind-bridge.tech/api/session/SESSION_ID/ \
     -H "Authorization: Token YOUR_TOKEN"
   ```

5. **期待される結果**:
   ```json
   {
     "id": "SESSION_ID",
     "realtime_mode": false,  // ← WebSocket切断後は false
     ...
   }
   ```

---

### テスト 4: モード切り替えの動作確認

1. **テキストモード → リアルタイムモード**:
   - セッション開始（テキストモード）
   - `realtime_mode` が `false` であることを確認
   - リアルタイムモードに切り替え
   - WebSocket接続
   - `realtime_mode` が `true` になることを確認

2. **リアルタイムモード → テキストモード**:
   - WebSocket切断
   - `realtime_mode` が `false` に戻ることを確認
   - テキストモードで会話継続
   - `realtime_mode` が `false` のままであることを確認

---

## 📊 検証結果の記録

| テスト項目 | 結果 | 備考 |
|-----------|------|------|
| セッション作成時の初期値 | ⬜ | realtime_mode=false |
| WebSocket接続時の更新 | ⬜ | realtime_mode=true |
| WebSocket切断時の更新 | ⬜ | realtime_mode=false |
| モード切り替え動作 | ⬜ | 正常に切り替わる |

---

## 🎯 成功条件

- ✅ SessionSerializer に `realtime_mode` が含まれている
- ✅ API経由で `realtime_mode` の状態を取得できる
- ✅ WebSocket接続時に `realtime_mode` が `True` になる
- ✅ WebSocket切断時に `realtime_mode` が `False` になる
- ✅ ログに状態更新が記録される

---

## 🔧 トラブルシューティング

### エラー: `Session XXXX not found for user YYYY`
- **原因**: セッションIDが無効、または他のユーザーのセッション
- **対処**: 正しいセッションIDを使用しているか確認

### エラー: `Failed to update session realtime_mode`
- **原因**: データベース接続エラー、またはモデル定義の不整合
- **対処**: マイグレーションが適用されているか確認
  ```bash
  docker compose exec web python manage.py showmigrations spin
  ```

### `realtime_mode` が更新されない
- **原因**: `session_id` がWebSocket接続時に渡されていない
- **対処**: フロントエンドのWebSocket接続URLを確認
  ```javascript
  // 正しい例
  const wsUrl = `wss://salesmind.mind-bridge.tech/ws/realtime/?token=${authToken}&session_id=${currentSessionId}`;
  ```


