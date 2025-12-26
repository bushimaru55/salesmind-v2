# メールサーバー設定ガイド

## 現在の構成

Postfixメールサーバーコンテナが構築され、Djangoアプリケーションから使用できるようになっています。

## メールが届かない問題

### 原因

1. **ポート25のブロック**: 多くのクラウド環境（AWS、GCP、Azureなど）では、ポート25（SMTP）がデフォルトでブロックされています。
2. **DNS解決の問題**: PostfixがMXレコードを解決できない場合があります。
3. **外部メールサーバーへの直接送信**: ブロックされたポートを使用して直接送信しようとしています。

### 解決策: SMTPリレーホストの使用

Postfixにリレーホストを設定し、外部SMTPサーバー（Gmail、SendGrid、Mailgunなど）を経由してメールを送信します。

## 設定方法

### 方法1: Gmail SMTPをリレーとして使用

`.env`ファイルに以下を追加：

```bash
# Gmail SMTPリレー設定
POSTFIX_RELAYHOST=[smtp.gmail.com]:587
POSTFIX_RELAYHOST_USER=your-email@gmail.com
POSTFIX_RELAYHOST_PASSWORD=your-app-password
```

**注意**: Gmailを使用する場合は、アプリパスワードが必要です。

### 方法2: SendGridをリレーとして使用

`.env`ファイルに以下を追加：

```bash
# SendGrid SMTPリレー設定
POSTFIX_RELAYHOST=[smtp.sendgrid.net]:587
POSTFIX_RELAYHOST_USER=apikey
POSTFIX_RELAYHOST_PASSWORD=your-sendgrid-api-key
```

### 方法3: 直接Djangoから外部SMTPを使用

メールサーバーコンテナをバイパスして、Djangoから直接外部SMTPサーバーを使用することもできます。

`.env`ファイルに以下を設定：

```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

そして、Djangoの設定で`EMAIL_HOST`を`mailserver`から外部SMTPサーバーに変更します。

## 推奨設定

本番環境では、**方法3（Djangoから直接外部SMTPを使用）**を推奨します。

理由：
- 設定が簡単
- リレーサーバーの管理が不要
- メール配信の信頼性が高い（SendGrid、Mailgunなど）

## メールサーバーコンテナの用途

メールサーバーコンテナは、以下の用途で使用できます：
- 内部ネットワーク内でのメール送信（開発環境）
- 将来的に独自ドメインでメールサーバーを運用する場合（DNS設定とポート25の開放が必要）

## トラブルシューティング

### メールが届かない場合

1. メールキューを確認：
   ```bash
   docker compose exec mailserver postqueue -p
   ```

2. メールログを確認：
   ```bash
   docker compose logs mailserver
   ```

3. DNS解決を確認：
   ```bash
   docker compose exec mailserver python3 -c "import socket; print(socket.gethostbyname('gmail.com'))"
   ```

### ポート25がブロックされている場合

- ホスティングプロバイダーにポート25の開放を依頼する
- または、SMTPリレーサーバー（ポート587または465）を使用する



