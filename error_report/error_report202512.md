# メール送信システム エラーレポート

**作成日**: 2025年12月23日  
**対象システム**: SalesMind メール送信機能（Postfix + Django）

---

## 📋 目次

1. [実行した作業の概要](#実行した作業の概要)
2. [実装した機能](#実装した機能)
3. [発生している問題](#発生している問題)
4. [問題の詳細分析](#問題の詳細分析)
5. [実施した対応](#実施した対応)
6. [現在の状態](#現在の状態)
7. [技術的な詳細](#技術的な詳細)
8. [次のステップ](#次のステップ)

---

## 実行した作業の概要

### 1. UserEmailモデルの実装

**目的**: 1ユーザーに対して複数のメールアドレスを管理し、その中から認証メール送信用のアドレスを選択できるようにする。

**実装内容**:
- `UserEmail`モデルを作成（`backend/spin/models.py`）
  - `user`: ユーザーとの外部キー
  - `email`: メールアドレス
  - `is_verification_email`: ログイン認証メール送信用フラグ（1ユーザーに1つまで）
  - `verified`: 認証済みフラグ
  - `verified_at`: 認証完了日時
  - 同一ユーザー内でのメールアドレス重複を防止（`unique_together = [['user', 'email']]`）

- マイグレーション実行
  - マイグレーションファイル: `backend/spin/migrations/0018_add_useremail_model.py`
  - データベースへの反映: 完了

### 2. Django管理画面の拡張

**実装内容**:
- `CustomUserAdmin`に`UserEmailInline`を追加
  - ユーザー詳細画面でメールアドレスをインライン表示・編集可能
  - フィールド: `email`, `is_verification_email`, `verified`, `verified_at`, `created_at`
  - 認証メール送信用のアドレスを選択できるチェックボックス

- `UserEmailAdmin`を作成
  - メールアドレス一覧画面での管理
  - 検索・フィルタリング機能
  - 直接編集・削除が可能

**ファイル**: `backend/spin/admin.py`

### 3. メール送信機能の修正

**実装内容**:
- `send_verification_email`関数を修正（`backend/spin/email_service.py`）
  - `UserEmail.is_verification_email=True`のメールアドレスを使用
  - UserEmailが存在しない場合は既存の`user.email`を使用（後方互換性）

### 4. Django設定の変更

**実装内容**:
- `backend/salesmind/settings.py`を修正
  - 外部SMTP（Gmail）ではなく、システムドメインのPostfixメールサーバーコンテナ（`mailserver`）を使用するように変更
  - `EMAIL_HOST = 'mailserver'`（Dockerコンテナ名）
  - `EMAIL_PORT = 25`（SMTP）
  - 認証不要（内部ネットワーク経由）

### 5. システムドメインのメールアドレス作成

**実装内容**:
- `test@salesmind.mind-bridge.tech`というメールアドレスを`admin`ユーザーに追加
- 認証メール送信用に設定（`is_verification_email=True`）

---

## 実装した機能

### ✅ 完了した機能

1. **複数メールアドレス管理**
   - 1ユーザーに対して複数のメールアドレスを登録可能
   - 同一ユーザー内での重複を防止

2. **認証メール送信先の選択**
   - `is_verification_email`フラグで認証メール送信用のアドレスを1つ指定可能
   - 1ユーザーに1つのみ設定可能（他のメールアドレスのフラグは自動的にFalseになる）

3. **管理者画面での管理**
   - ユーザー詳細画面でメールアドレスの追加・編集・削除が可能
   - メールアドレス一覧画面での管理も可能

4. **メール送信機能**
   - DjangoからPostfixへのメール送信は成功
   - システムドメインのメールアドレスからメールを送信可能

---

## 発生している問題

### ❌ 現在の主要な問題

**問題**: Postfixが実行時に外部ドメイン（gmail.com）のMXレコードを解決できない

**症状**:
- メールがキューに滞留（`deferred` status）
- エラーメッセージ: `Host or domain name not found. Name service error for name=gmail.com type=MX: Host not found, try again`
- `dig`コマンドではDNS解決が成功するが、Postfixの実行時には失敗

**影響範囲**:
- 外部メールアドレス（Gmailなど）へのメール送信が失敗
- メールがキューに滞留し続ける

---

## 問題の詳細分析

### 1. DNS解決の不一致

**状況**:
- 起動時のDNS解決テスト（`host gmail.com`）: ✅ 成功
- `dig gmail.com MX`コマンド: ✅ 成功
- Postfixの実行時のMXレコード解決: ❌ 失敗

**原因の仮説**:
1. Postfixが起動時に読み込んだDNSリゾルバー設定が、実行時には無効になっている
2. Dockerの内部DNS（127.0.0.11）が外部DNS（8.8.8.8, 8.8.4.4）にフォワードする際のタイミング問題
3. Postfixのプロセスが`/etc/resolv.conf`を起動時にキャッシュしており、実行時のDNS解決に反映されていない

### 2. `/etc/resolv.conf`の管理

**現在の状態**:
```
nameserver 127.0.0.11
search .
options edns0 trust-ad ndots:0

# Based on host file: '/etc/resolv.conf' (internal resolver)
# ExtServers: [8.8.8.8 8.8.4.4]
# Overrides: [nameservers]
```

- Docker Engineが自動生成
- 内部DNS（127.0.0.11）を使用
- ExtServersとして8.8.8.8と8.8.4.4が設定されているが、実際の解決時に使用されていない可能性

### 3. docker-compose.ymlの設定

**現在の設定**:
```yaml
mailserver:
  dns:
    - 8.8.8.8
    - 8.8.4.4
```

- DNS設定は正しく指定されている
- しかし、`/etc/resolv.conf`には反映されていない（127.0.0.11が使用されている）

---

## 実施した対応

### 1. start.shスクリプトの修正

**試行1**: `/etc/resolv.conf`をスクリプト内で上書き
- **結果**: Dockerが自動的に上書きしてしまうため効果なし

**試行2**: Postfix起動後に`/etc/resolv.conf`を修正して`postfix reload`
- **結果**: `postfix reload`ではDNS設定が反映されない（Postfixは起動時にDNSリゾルバーを内部保持）

**試行3**: start.shスクリプトを簡素化し、docker-compose.ymlのDNS設定を信頼
- **結果**: 問題が継続

### 2. Postfix設定の調整

**試行した設定**:
- `smtp_dns_support_level = enabled`
- `smtp_host_lookup = dns`
- `smtp_connect_timeout = 30s`

**削除した設定**（エラーを引き起こしたもの）:
- `smtp_dns_reply_filter = dns_sortlist` → 設定エラーを引き起こしたため削除
- `smtp_tcp_resolution_limit = 5` → 未使用パラメータ警告のため削除
- `log_verbose_level = 2` → 未使用パラメータ警告のため削除

### 3. メールキューのクリア

**実施内容**:
- `postsuper -d ALL`で滞留メールを削除
- 再送テストを実施

**結果**: メール送信は成功するが、キューに滞留してしまう

---

## 現在の状態

### ✅ 正常に動作している部分

1. **Postfixの起動**: 正常
2. **Django → Postfixの接続**: 正常（メールはPostfixに受け取られる）
3. **DNS解決テスト**: `dig`コマンドや`host`コマンドでは成功
4. **システムドメインのメールアドレス**: 正常に作成されている

### ❌ 問題が残っている部分

1. **PostfixのMXレコード解決**: 実行時に失敗
2. **メールキュー**: メールが`deferred` statusで滞留
3. **外部メール送信**: Gmailなどへの送信が失敗

### 現在のエラーログ

```
Dec 23 10:17:48 mail postfix/smtp[190]: ADA84145176: to=<job.kouhei.onishi@gmail.com>, relay=none, delay=0.01, delays=0.01/0/0/0, dsn=4.4.3, status=deferred (Host or domain name not found. Name service error for name=gmail.com type=MX: Host not found, try again)
```

### メールキューの状態

```
-Queue ID-  --Size-- ----Arrival Time---- -Sender/Recipient-------
ADA84145176     992 Tue Dec 23 10:17:48  test@salesmind.mind-bridge.tech
(Host or domain name not found. Name service error for name=gmail.com type=MX: Host not found, try again)
                                         job.kouhei.onishi@gmail.com
```

---

## 技術的な詳細

### PostfixのDNS解決メカニズム

1. **起動時の動作**:
   - Postfixは起動時に`/etc/resolv.conf`を読み込み
   - DNSリゾルバーを内部に保持
   - `postfix reload`ではDNS設定は再読み込みされない

2. **実行時の動作**:
   - MXレコード解決時に内部保持しているDNSリゾルバーを使用
   - `/etc/resolv.conf`の変更は反映されない（コンテナ再起動が必要）

### DockerのDNS解決

1. **Docker内部DNS（127.0.0.11）**:
   - Dockerデーモンが提供する内部DNSサーバー
   - 外部DNS（8.8.8.8など）にフォワードするはずだが、タイミングによって失敗する可能性

2. **docker-compose.ymlのdns設定**:
   - コンテナ内の`/etc/resolv.conf`に反映されるはず
   - しかし、Docker Engineが自動生成するため、実際の反映が保証されない場合がある

### 現在の設定ファイル

#### docker-compose.yml（mailserverサービス）
```yaml
mailserver:
  build: ./mailserver
  container_name: salesmind_mailserver
  hostname: mail.salesmind.mind-bridge.tech
  domainname: salesmind.mind-bridge.tech
  ports:
    - "25:25"
    - "587:587"
    - "465:465"
  environment:
    - POSTFIX_MYHOSTNAME=mail.salesmind.mind-bridge.tech
    - POSTFIX_MYDOMAIN=salesmind.mind-bridge.tech
  dns:
    - 8.8.8.8
    - 8.8.4.4
  volumes:
    - mailserver_data:/var/spool/postfix
    - mailserver_logs:/var/log/postfix
  networks:
    - salesmind_network
  restart: unless-stopped
```

#### mailserver/start.sh（Postfix設定スクリプト）
```bash
#!/bin/bash
# Postfixの基本設定
postconf -e "myhostname = $MYHOSTNAME"
postconf -e "mydomain = $MYDOMAIN"
# ... その他の設定

# DNS解決設定
postconf -e "smtp_dns_support_level = enabled"
postconf -e "smtp_host_lookup = dns"
postconf -e "smtp_connect_timeout = 30s"

# ログをstdoutに出力
postconf -e "maillog_file = /dev/stdout"

# Postfixをフォアグラウンドで起動
exec /usr/sbin/postfix start-fg
```

---

## 次のステップ

### 推奨される対応策

#### 1. DockerデーモンのDNS設定確認

ホストOSレベルでDockerデーモンのDNS設定を確認する。

**確認コマンド**:
```bash
# DockerデーモンのDNS設定を確認
cat /etc/docker/daemon.json 2>/dev/null || echo "daemon.jsonが見つかりません"
```

**対応方法**:
```json
{
  "dns": ["8.8.8.8", "8.8.4.4"]
}
```

#### 2. コンテナ内の`/etc/resolv.conf`を直接確認・修正

**確認**:
```bash
docker compose exec mailserver cat /etc/resolv.conf
```

**期待値**:
```
nameserver 8.8.8.8
nameserver 8.8.4.4
```

**現在の実際の値**:
```
nameserver 127.0.0.11
```

#### 3. ネットワークモードの確認

**確認コマンド**:
```bash
docker compose exec mailserver cat /etc/resolv.conf
docker network inspect salesmind_salesmind_network | grep -A 5 "DNS"
```

#### 4. 代替案: リレーホストの使用

Postfixにリレーホスト（外部SMTPサーバー）を設定し、直接外部送信を回避する方法。

**設定例**:
```bash
postconf -e "relayhost = [smtp.gmail.com]:587"
# 認証が必要な場合は、sasl設定も追加
```

ただし、この場合はシステムドメインから直接送信する要件と矛盾する可能性がある。

#### 5. 代替案: 外部SMTPサービス（SendGrid、Mailgunなど）の使用

システムドメインから直接送信する要件を満たせない場合は、外部SMTPサービスを使用する方法。

---

## 補足情報

### 確認済みの動作

- ✅ DjangoからPostfixへのSMTP接続: 正常
- ✅ Postfixの起動: 正常
- ✅ メールのキューイング: 正常
- ✅ DNS解決テスト（`dig`, `host`コマンド）: 正常
- ❌ Postfix実行時のMXレコード解決: 失敗

### ログ出力の設定

- Postfixのログは`/dev/stdout`に出力されるように設定済み
- `docker compose logs mailserver`で確認可能

### 関連ファイル

- `backend/spin/models.py`: UserEmailモデル定義
- `backend/spin/admin.py`: 管理者画面の設定
- `backend/spin/email_service.py`: メール送信機能
- `backend/salesmind/settings.py`: Django設定（メール設定含む）
- `mailserver/start.sh`: Postfix起動スクリプト
- `docker-compose.yml`: Docker Compose設定

---

## 結論

システムドメインのメールアドレス管理機能は正常に実装され、DjangoからPostfixへのメール送信も成功しています。しかし、Postfixが実行時に外部ドメインのMXレコードを解決できない問題が残っています。

この問題は、DockerのDNS解決メカニズムとPostfixのDNS解決タイミングの不一致によるものと考えられます。docker-compose.ymlでDNS設定を指定しているにもかかわらず、実際の`/etc/resolv.conf`には反映されていない（127.0.0.11が使用されている）ことが根本原因の可能性が高いです。

**推奨される対応**:
1. DockerデーモンのDNS設定を確認・修正
2. ネットワーク設定を確認
3. 必要に応じて、リレーホストまたは外部SMTPサービスの使用を検討



