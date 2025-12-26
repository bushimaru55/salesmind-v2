# チャットビュー周りの不整合分析レポート

## 🔍 発見された不整合

### 1. **SessionSerializer に `realtime_mode` フィールドが欠落**

**問題箇所**: `backend/spin/serializers.py` Line 67-69

```python
class SessionSerializer(serializers.ModelSerializer):
    # ...
    class Meta:
        model = Session
        fields = ['id', 'user', 'mode', 'industry', 'value_proposition', 'customer_persona', 
                  'customer_pain', 'status', 'started_at', 'finished_at', 'created_at',
                  'company_id', 'company', 'company_analysis', 'success_probability', 
                  'last_analysis_reason', 'current_spin_stage']
        # ❌ 'realtime_mode' が含まれていない！
```

**影響**:
- Session モデルには `realtime_mode` フィールドが存在（Line 447 in models.py）
- しかし、API経由でこのフィールドを読み書きできない
- フロントエンドがセッション情報を取得しても `realtime_mode` の状態がわからない

---

### 2. **フロントエンドのセッション開始時に `realtime_mode` を送信していない**

**問題箇所**: `frontend/app.js` Line 1087-1098

```javascript
const response = await fetch(`${API_BASE_URL}/session/start/`, {
    method: 'POST',
    headers: {
        'Authorization': `Token ${authToken}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        industry,
        value_proposition,
        customer_persona: customer_persona || undefined,
        customer_pain: customer_pain || undefined
        // ❌ realtime_mode が含まれていない！
    })
});
```

**影響**:
- すべてのセッションがデフォルト値 `realtime_mode=False` で作成される
- リアルタイムモードに切り替えてもバックエンドのセッション状態は更新されない

---

### 3. **`conversationMode` と `realtime_mode` の不一致**

**問題箇所**: 
- `frontend/app.js` Line 15: `let conversationMode = 'text';`
- `frontend/app-realtime.js` Line 14: `conversationMode = mode;`

**現状の動作**:
1. フロントエンドで `conversationMode` を 'realtime' に変更
2. しかし、バックエンドの `session.realtime_mode` は `False` のまま
3. WebSocket接続しても、セッションの `realtime_mode` フィールドは更新されない

**影響**:
- セッション情報とUI状態が乖離する
- 将来的に realtime_mode に基づいた処理分岐を追加する際に不具合が発生する可能性

---

### 4. **WebSocket Consumer でのセッション状態更新がない**

**問題箇所**: `backend/spin/consumers.py`

**確認結果**:
- WebSocket接続時にセッションの `realtime_mode` を `True` に更新する処理がない
- WebSocket切断時にセッションの `realtime_mode` を `False` に戻す処理がない

**影響**:
- リアルタイムモードで会話中かどうかをバックエンドで判定できない
- セッション履歴を見ても、どのメッセージがリアルタイムモードで送信されたかわからない

---

## 📋 修正提案

### オプション A: セッション作成時に決定する方式

**メリット**: シンプルな設計
**デメリット**: セッション途中でのモード切り替えができない

1. SessionSerializer に `realtime_mode` フィールドを追加
2. フロントエンドでセッション開始前にモードを選択させる
3. セッション作成時に `realtime_mode` を送信

### オプション B: 動的切り替え方式（推奨）

**メリット**: 柔軟性が高い、ユーザー体験が向上
**デメリット**: 実装がやや複雑

1. SessionSerializer に `realtime_mode` フィールドを追加（read_only_fields に含める）
2. WebSocket接続時にセッションの `realtime_mode` を `True` に更新
3. WebSocket切断時にセッションの `realtime_mode` を `False` に更新
4. フロントエンドの `conversationMode` はUI状態管理のみに使用

### オプション C: 完全分離方式

**メリット**: 責務が明確
**デメリット**: データの整合性が保証されない

1. `realtime_mode` をセッション単位ではなくメッセージ単位で管理
2. ChatMessage モデルに `is_realtime` フィールドを追加
3. リアルタイムで送信されたメッセージには `is_realtime=True` を設定

---

## 🎯 推奨修正内容（オプション B）

### 1. SessionSerializer の修正

```python
class SessionSerializer(serializers.ModelSerializer):
    # ...
    class Meta:
        model = Session
        fields = ['id', 'user', 'mode', 'realtime_mode', 'industry', 'value_proposition', 
                  'customer_persona', 'customer_pain', 'status', 'started_at', 'finished_at', 
                  'created_at', 'company_id', 'company', 'company_analysis', 
                  'success_probability', 'last_analysis_reason', 'current_spin_stage']
        read_only_fields = ['id', 'user', 'status', 'started_at', 'finished_at', 'created_at', 
                            'company', 'company_analysis', 'success_probability', 
                            'last_analysis_reason', 'current_spin_stage', 'realtime_mode']
```

### 2. WebSocket Consumer の修正

```python
async def connect(self):
    # ... (既存の接続処理)
    
    # セッションを realtime_mode = True に更新
    await database_sync_to_async(self._update_session_realtime_mode)(True)
    
    await self.accept()

async def disconnect(self, close_code):
    # セッションを realtime_mode = False に更新
    await database_sync_to_async(self._update_session_realtime_mode)(False)
    
    # ... (既存の切断処理)

def _update_session_realtime_mode(self, is_realtime):
    """セッションのリアルタイムモードを更新"""
    try:
        self.session.realtime_mode = is_realtime
        self.session.save(update_fields=['realtime_mode'])
        logger.info(f"Session {self.session_id} realtime_mode updated to {is_realtime}")
    except Exception as e:
        logger.error(f"Failed to update session realtime_mode: {e}")
```

### 3. フロントエンドの修正（オプション）

```javascript
// セッション情報を取得して realtime_mode を表示
async function updateSessionStatus() {
    const response = await fetch(`${API_BASE_URL}/session/${currentSessionId}/`, {
        headers: {
            'Authorization': `Token ${authToken}`
        }
    });
    const session = await response.json();
    
    // UI更新
    if (session.realtime_mode) {
        console.log('このセッションはリアルタイムモードです');
    }
}
```

---

## 📊 優先度

| 項目 | 優先度 | 理由 |
|------|--------|------|
| SessionSerializer 修正 | 🔴 高 | 現在のAPI仕様の不整合を解消 |
| WebSocket Consumer 修正 | 🟡 中 | 将来的な機能拡張に必要 |
| フロントエンド修正 | 🟢 低 | 現時点では動作に影響しない |

---

## ✅ 修正実施判断

**今すぐ修正すべきか？**
- **YES**: リアルタイムモードの状態をバックエンドで正確に管理したい場合
- **NO**: 現在の動作に問題がなく、将来のリファクタリングで対応する場合

**ユーザーへの質問**:
1. セッション途中でのモード切り替えを許可しますか？（推奨: YES）
2. セッション履歴にリアルタイムモードの記録を残しますか？（推奨: YES）
3. 今すぐ修正しますか、それとも既存のエラー解決を優先しますか？


