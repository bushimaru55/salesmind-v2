# GitHub Personal Access Token 取得手順

## 📋 概要
Gitリポジトリへのプッシュを行うために、GitHub Personal Access Token（PAT）が必要です。
このドキュメントでは、PATの作成から使用までの手順を説明します。

---

## 🔑 ステップ1: GitHubにログイン
1. ブラウザで [GitHub](https://github.com) にアクセス
2. アカウントでログイン

---

## 🔑 ステップ2: Settingsページに移動
1. GitHubの右上にあるプロフィール画像をクリック
2. ドロップダウンメニューから **Settings** を選択
   - または直接 https://github.com/settings/profile にアクセス

---

## 🔑 ステップ3: Developer settingsに移動
1. Settingsページの左側のメニューを下にスクロール
2. **Developer settings** をクリック
   - または直接 https://github.com/settings/apps にアクセス

---

## 🔑 ステップ4: Personal access tokensに移動
1. Developer settingsページの左側メニューから **Personal access tokens** をクリック
2. **Tokens (classic)** を選択
   - または直接 https://github.com/settings/tokens にアクセス

---

## 🔑 ステップ5: 新しいトークンを生成
1. **Generate new token** ボタンをクリック
2. **Generate new token (classic)** を選択
   - 注意: Fine-grained tokensではなく、classic tokensを選択してください

---

## 🔑 ステップ6: トークンの設定

### Note（メモ）の入力
- **Note**: トークンの説明を入力
  - 例: `salesmind-v2-push` または `SalesMind Git Push`

### Expiration（有効期限）の設定
- **Expiration**: トークンの有効期限を選択
  - 推奨: `90 days` または `No expiration`（長期使用の場合）

### Scopes（権限）の設定
以下の権限にチェックを入れます：

#### ✅ 必須権限
- [x] **repo** - Full control of private repositories
  - これには以下のサブ権限が含まれます：
    - `repo:status` - Access commit status
    - `repo_deployment` - Access deployment status
    - `public_repo` - Access public repositories
    - `repo:invite` - Access repository invitations
    - `security_events` - Read and write security events

**重要**: `repo` 権限にチェックを入れると、自動的に必要なサブ権限も有効になります。

---

## 🔑 ステップ7: トークンを生成
1. ページの下部にある **Generate token** ボタンをクリック
2. **重要**: 表示されたトークンをすぐにコピーしてください
   - トークンは一度しか表示されません
   - ページを閉じると再表示できません

---

## 🔑 ステップ8: トークンの保存
生成されたトークンを安全な場所に保存してください。

**例**: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## 🚀 ステップ9: トークンを使用してプッシュ

トークンを取得したら、以下のコマンドでプッシュできます：

### 方法A: リモートURLにトークンを埋め込む（一時的）
```bash
cd /opt/salesmind
git remote set-url origin https://bushimaru55:<YOUR_TOKEN>@github.com/bushimaru55/salesmind-v2.git
git push origin main
```

**注意**: この方法はコマンド履歴にトークンが残るため、一時的な使用に適しています。

### 方法B: Git Credential Helperを使用（推奨）
```bash
cd /opt/salesmind
git config --global credential.helper store
git push origin main
# Username: bushimaru55
# Password: <YOUR_TOKEN>（Personal Access Tokenを入力）
```

この方法では、認証情報が `~/.git-credentials` に保存されます。

### 方法C: 環境変数を使用
```bash
cd /opt/salesmind
export GIT_ASKPASS=echo
export GIT_USERNAME=bushimaru55
export GIT_PASSWORD=<YOUR_TOKEN>
git -c credential.helper='!f() { echo username=$GIT_USERNAME; echo password=$GIT_PASSWORD; }; f' push origin main
```

---

## 🔒 セキュリティに関する注意事項

1. **トークンの機密性**
   - Personal Access Tokenはパスワードと同等の権限を持ちます
   - 他人と共有しないでください
   - 公開リポジトリやコミットメッセージに含めないでください

2. **トークンの管理**
   - 定期的にトークンの有効期限を確認してください
   - 不要になったトークンは削除してください
   - GitHub Settings > Developer settings > Personal access tokens で管理できます

3. **漏洩時の対応**
   - トークンが漏洩した場合は、すぐにGitHubでトークンを削除/無効化してください
   - 新しいトークンを生成してください

---

## 📝 トラブルシューティング

### エラー: "Authentication failed"
- トークンが正しくコピーされているか確認
- トークンに `repo` 権限があるか確認
- トークンの有効期限を確認

### エラー: "Permission denied"
- リポジトリへのアクセス権限を確認
- トークンの権限スコープを確認

### トークンを忘れた場合
- GitHub Settings > Developer settings > Personal access tokens で確認
- 既存のトークンは表示されませんが、削除/再生成が可能です

---

## ✅ チェックリスト

プッシュ前に以下を確認してください：

- [ ] GitHubにログイン済み
- [ ] Personal Access Tokenを生成済み
- [ ] トークンに `repo` 権限がある
- [ ] トークンを安全に保存した
- [ ] リモートリポジトリURLが正しい（https://github.com/bushimaru55/salesmind-v2.git）

---

## 📞 サポート

問題が発生した場合：
1. 上記のトラブルシューティングを確認
2. GitHubのドキュメントを参照: https://docs.github.com/en/authentication
3. トークンの権限設定を再確認



