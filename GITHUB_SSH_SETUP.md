# GitHub SSH鍵登録手順

## 📋 概要
SSH鍵を使用してGitリポジトリへのプッシュを行う方法です。
Personal Access Tokenよりも安全で、一度設定すれば長期間使用できます。

---

## 🔑 ステップ1: SSH公開鍵を確認
既にSSH鍵が生成されています。公開鍵は以下の通りです：

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFU3NI2u6NFDCp8Ke2hfwTVgueJbq7Esda4XiLFWXmTP salesmind-v2
```

この公開鍵をコピーしてください。

---

## 🔑 ステップ2: GitHub Settingsに移動
1. ブラウザで [GitHub](https://github.com) にアクセス
2. アカウントでログイン
3. 右上のプロフィール画像をクリック
4. **Settings** を選択
   - または直接 https://github.com/settings/profile にアクセス

---

## 🔑 ステップ3: SSH and GPG keysに移動
1. Settingsページの左側メニューを下にスクロール
2. **SSH and GPG keys** をクリック
   - または直接 https://github.com/settings/keys にアクセス

---

## 🔑 ステップ4: 新しいSSH鍵を追加
1. **New SSH key** ボタンをクリック

---

## 🔑 ステップ5: SSH鍵の情報を入力

### Title（タイトル）
- **Title**: SSH鍵の識別名を入力
  - 例: `salesmind-v2-server` または `SalesMind Production Server`
  - 複数の鍵を管理する際に識別しやすい名前を付けます

### Key type（鍵の種類）
- **Key type**: **Authentication Key** を選択（通常はデフォルト）

### Key（鍵）
- **Key**: 以下の公開鍵を貼り付けます：

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFU3NI2u6NFDCp8Ke2hfwTVgueJbq7Esda4XiLFWXmTP salesmind-v2
```

**重要**: 
- 公開鍵全体（`ssh-ed25519` から最後まで）をコピーしてください
- 改行や余分なスペースが入らないように注意してください

---

## 🔑 ステップ6: SSH鍵を追加
1. **Add SSH key** ボタンをクリック
2. 必要に応じてGitHubのパスワードを入力して確認

---

## 🔑 ステップ7: SSH接続をテスト
SSH鍵が正しく登録されたか確認します：

```bash
ssh -T git@github.com
```

**成功時のメッセージ**:
```
Hi bushimaru55! You've successfully authenticated, but GitHub does not provide shell access.
```

このメッセージが表示されれば、SSH認証は成功しています。

---

## 🚀 ステップ8: リモートURLをSSHに変更してプッシュ

SSH鍵が登録されたら、リモートURLをSSHに変更してプッシュします：

```bash
cd /opt/salesmind
git remote set-url origin git@github.com:bushimaru55/salesmind-v2.git
git push origin main
```

---

## 🔒 セキュリティに関する注意事項

1. **秘密鍵の管理**
   - 秘密鍵（`~/.ssh/id_ed25519`）は絶対に他人と共有しないでください
   - 秘密鍵はパスワードで保護することを推奨します（今回はパスフレーズなしで生成）

2. **公開鍵の共有**
   - 公開鍵（`.pub`ファイル）は安全に共有できます
   - GitHubに登録するのは公開鍵のみです

3. **鍵のローテーション**
   - 定期的にSSH鍵を更新することを推奨します
   - 不要になった鍵はGitHubから削除してください

---

## 📝 トラブルシューティング

### エラー: "Permission denied (publickey)"
- SSH公開鍵がGitHubに正しく登録されているか確認
- 公開鍵の内容が正しくコピーされているか確認（改行やスペースがないか）
- SSH接続テストを実行: `ssh -T git@github.com`

### エラー: "Host key verification failed"
- GitHubのホスト鍵を追加:
  ```bash
  ssh-keyscan github.com >> ~/.ssh/known_hosts
  ```

### 複数のSSH鍵を管理する場合
- `~/.ssh/config` ファイルで鍵を管理できます
- 例:
  ```
  Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
  ```

---

## ✅ チェックリスト

SSH鍵登録前に以下を確認してください：

- [ ] SSH公開鍵をコピーした
- [ ] GitHubにログイン済み
- [ ] SSH and GPG keysページにアクセスした
- [ ] 公開鍵全体を正しく貼り付けた
- [ ] Add SSH keyボタンをクリックした
- [ ] SSH接続テストが成功した

---

## 📞 サポート

問題が発生した場合：
1. 上記のトラブルシューティングを確認
2. GitHubのドキュメントを参照: https://docs.github.com/en/authentication/connecting-to-github-with-ssh
3. SSH接続テストの結果を確認



