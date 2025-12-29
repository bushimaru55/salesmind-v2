# メール送信システム 状況レポート #02

**作成日**: 2025年12月23日  
**対象システム**: SalesMind メール送信機能（Postfix + Django）  
**前回レポート**: `error_report202512.md`

---

## 📋 目次

1. [問題の解決](#問題の解決)
2. [原因の特定](#原因の特定)
3. [実施した対応](#実施した対応)
4. [対応結果](#対応結果)
5. [現在の状態](#現在の状態)
6. [新たに判明した課題](#新たに判明した課題)
7. [技術的な詳細](#技術的な詳細)
8. [次のステップ](#次のステップ)

---

## 問題の解決

### ✅ 解決した問題

**問題**: Postfixが実行時に外部ドメイン（gmail.com）のMXレコードを解決できない

**症状（修正前）**:
- メールがキューに滞留（`deferred` status）
- エラーメッセージ: `Host or domain name not found. Name service error for name=gmail.com type=MX: Host not found, try again`
- `dig`コマンドではDNS解決が成功するが、Postfixの実行時には失敗

**解決状況**: ✅ **完全に解決**

---

## 原因の特定

### 根本原因

**Postfixのchroot（隔離実行）によるDNS解決失敗**

Postfixの`smtp`プロセスは、設定により`/var/spool/postfix`配下でchroot（隔離実行）されます。chroot環境では、通常の`/etc/resolv.conf`ではなく、**`/var/spool/postfix/etc/resolv.conf`**を参照します。

### 現状確認結果

```bash
### queue_directory
/var/spool/postfix

### master.cf smtp lines
12:smtp      inet  n       -       y       -       -       smtpd
58:smtp      unix  -       -       y       -       -       smtp  # chroot=y が有効
68:lmtp      unix  -       -       y       -       -       lmtp

### chroot etc dir（修正前）
total 8
drwxr-xr-x  2 root root 4096 Jan 29  2024 .
drwxr-xr-x 20 root root 4096 Dec 23 10:02 ..
# ファイルが存在しない！
```

### 問題のメカニズム

1. **通常のDNS解決**: `dig`コマンドや`host`コマンドは通常の`/etc/resolv.conf`を使用 → ✅ 成功
2. **Postfix smtpプロセスのDNS解決**: chroot環境内の`/var/spool/postfix/etc/resolv.conf`を使用 → ❌ ファイルが存在しないため失敗

### 重要な事実

- `/etc/resolv.conf`が`nameserver 127.0.0.11`（Docker内部DNS）のままなのは**正常な動作**
- Dockerの内部DNS（127.0.0.11）が外部DNS（8.8.8.8, 8.8.4.4）にフォワードする仕組み
- `dig gmail.com MX`が成功するなら、コンテナのDNSは正常に動作している
- 問題は、**chroot環境内にresolv.confが存在しないこと**

---

## 実施した対応

### 1. mailserver/start.shの修正

Postfix起動前に、chroot環境内に必要なDNS設定ファイルをコピーする処理を追加しました。

**追加したコード**（`exec /usr/sbin/postfix start-fg`の直前）:

```bash
# --- chroot DNS fix (IMPORTANT) ---
# Postfix の smtp プロセスが chroot で動く場合、/var/spool/postfix/etc/resolv.conf が必要
QUEUE_DIR="$(postconf -h queue_directory 2>/dev/null || echo /var/spool/postfix)"
mkdir -p "${QUEUE_DIR}/etc"

# DNS resolver for chrooted postfix processes (smtp, pickup, etc.)
cp -f /etc/resolv.conf "${QUEUE_DIR}/etc/resolv.conf"
cp -f /etc/hosts      "${QUEUE_DIR}/etc/hosts" || true
cp -f /etc/nsswitch.conf "${QUEUE_DIR}/etc/nsswitch.conf" || true

# optional: ensure permissions
chmod 0644 "${QUEUE_DIR}/etc/resolv.conf" || true

echo "Chroot DNS configuration files copied to ${QUEUE_DIR}/etc/"
```

### 2. コンテナの再ビルドと再作成

```bash
docker compose up -d --force-recreate --build mailserver
```

### 3. 確認コマンドの実行

#### chroot環境内のファイル確認

```bash
ls -la /var/spool/postfix/etc
cat /var/spool/postfix/etc/resolv.conf
```

**結果**: ✅ すべてのファイルが正常にコピーされていることを確認

---

## 対応結果

### ✅ 成功した部分

1. **DNS解決の復旧**
   - PostfixのsmtpプロセスがMXレコードを正常に解決
   - `relay=gmail-smtp-in.l.google.com[108.177.97.27]:25` として接続成功

2. **メールキューの解消**
   - `deferred` statusのメールが消失
   - メールキューが空になる（`Mail queue is empty`）

3. **メール送信の成功**
   - DjangoからPostfixへのメール送信: ✅ 成功
   - PostfixからGmailサーバーへの接続: ✅ 成功

### 修正前後の比較

#### 修正前

```
status=deferred (Host or domain name not found. Name service error for name=gmail.com type=MX: Host not found, try again)
```

メールがキューに滞留し続ける。

#### 修正後

```
Dec 23 10:24:22 mail postfix/smtp[200]: 498E41451E9: to=<job.kouhei.onishi@gmail.com>, relay=gmail-smtp-in.l.google.com[108.177.97.26]:25, delay=2, delays=0/0/1/0.94, dsn=5.7.26, status=bounced
```

- DNS解決: ✅ 成功（GmailのMXレコードを解決）
- メールサーバーへの接続: ✅ 成功
- メールキュー: ✅ 滞留なし（即座に処理される）

---

## 現在の状態

### ✅ 正常に動作している機能

1. **Postfixの起動**: 正常
2. **DNS解決**: 正常（chroot環境内でも動作）
3. **Django → Postfixの接続**: 正常
4. **Postfix → 外部メールサーバーの接続**: 正常
5. **メールキュー**: 正常（滞留なし）
6. **システムドメインのメールアドレス管理**: 正常

### 確認された動作

- ✅ `/var/spool/postfix/etc/resolv.conf`が存在し、正しく設定されている
- ✅ `/var/spool/postfix/etc/hosts`が存在
- ✅ `/var/spool/postfix/etc/nsswitch.conf`が存在
- ✅ PostfixのsmtpプロセスがGmailサーバーに接続できる
- ✅ MXレコード解決が正常に動作

---

## 新たに判明した課題

### ⚠️ SPF/DKIM認証の問題

メールは正常にGmailサーバーまで到達するようになりましたが、**SPF/DKIM認証が設定されていないため、Gmailがメールを拒否**しています。

**エラーメッセージ**:

```
550-5.7.26 Your email has been blocked because the sender is unauthenticated.
550-5.7.26 Gmail requires all senders to authenticate with either SPF or DKIM.
550-5.7.26 
550-5.7.26  Authentication results:
550-5.7.26   DKIM = did not pass
550-5.7.26   SPF [salesmind.mind-bridge.tech] with ip: [160.251.173.73] = did not pass
```

**状況**:
- DNS解決の問題: ✅ **解決済み**
- メールサーバーへの接続: ✅ **成功**
- SPF認証: ❌ **未設定**
- DKIM認証: ❌ **未設定**

**影響**:
- Gmailなどのメールプロバイダーがメールを拒否
- メールは送信されるが、受信側で拒否される

**これは別の問題**: DNS解決の問題とは独立した、メール認証の問題です。

---

## 技術的な詳細

### Postfixのchroot動作

1. **chrootとは**
   - プロセスを特定のディレクトリ（`/var/spool/postfix`）に隔離して実行
   - セキュリティ向上のための仕組み

2. **chroot環境でのファイル参照**
   - 通常: `/etc/resolv.conf`
   - chroot環境: `/var/spool/postfix/etc/resolv.conf`（相対パスとして`/etc/resolv.conf`）

3. **なぜdigコマンドは成功したのか**
   - `dig`コマンドは通常の環境で実行される
   - `/etc/resolv.conf`を参照するため、正常に動作

4. **なぜPostfixのsmtpプロセスは失敗したのか**
   - smtpプロセスはchroot環境で実行される
   - `/var/spool/postfix/etc/resolv.conf`が存在しなかったため、DNS解決が失敗

### DockerのDNS解決

1. **Docker内部DNS（127.0.0.11）**
   - Dockerデーモンが提供する内部DNSサーバー
   - コンテナ名解決と外部DNSフォワーディングを担当

2. **docker-compose.ymlのdns設定**
   - `dns: [8.8.8.8, 8.8.4.4]`を指定
   - これにより、127.0.0.11が8.8.8.8と8.8.4.4にフォワードする

3. **/etc/resolv.confの内容**
   ```
   nameserver 127.0.0.11
   # ExtServers: [8.8.8.8 8.8.4.4]
   ```
   - `nameserver 127.0.0.11`のままなのは正常
   - ExtServersとして外部DNSが設定されている

### 修正後の動作フロー

1. **コンテナ起動時**
   - `start.sh`が実行される
   - Postfix設定が行われる
   - **chroot環境内にresolv.confなどがコピーされる**（修正点）
   - Postfixが起動する

2. **メール送信時**
   - DjangoがPostfixにメールを送信
   - Postfixがメールをキューに追加
   - smtpプロセスがchroot環境で実行される
   - `/var/spool/postfix/etc/resolv.conf`を参照してDNS解決 ✅
   - MXレコードを解決してメールサーバーに接続 ✅

### 現在の設定ファイル

#### mailserver/start.sh（修正後）

```bash
#!/bin/bash
# ... Postfix設定 ...

# --- chroot DNS fix (IMPORTANT) ---
QUEUE_DIR="$(postconf -h queue_directory 2>/dev/null || echo /var/spool/postfix)"
mkdir -p "${QUEUE_DIR}/etc"

cp -f /etc/resolv.conf "${QUEUE_DIR}/etc/resolv.conf"
cp -f /etc/hosts      "${QUEUE_DIR}/etc/hosts" || true
cp -f /etc/nsswitch.conf "${QUEUE_DIR}/etc/nsswitch.conf" || true

chmod 0644 "${QUEUE_DIR}/etc/resolv.conf" || true

echo "Chroot DNS configuration files copied to ${QUEUE_DIR}/etc/"

exec /usr/sbin/postfix start-fg
```

#### /var/spool/postfix/etc/resolv.conf（chroot環境内）

```
# Generated by Docker Engine.
nameserver 127.0.0.11
search .
options edns0 trust-ad ndots:0

# Based on host file: '/etc/resolv.conf' (internal resolver)
# ExtServers: [8.8.8.8 8.8.4.4]
```

---

## 次のステップ

### 推奨される対応

#### 1. SPFレコードの設定（優先度高）

**目的**: 送信元メールサーバーのIPアドレスをDNSに登録し、送信元の正当性を証明

**必要な設定**:
- DNSのTXTレコードにSPFレコードを追加
- 例: `v=spf1 ip4:160.251.173.73 include:_spf.google.com ~all`

**設定場所**: 
- ドメインのDNS設定（`salesmind.mind-bridge.tech`）

**確認方法**:
```bash
dig TXT salesmind.mind-bridge.tech
```

#### 2. DKIM署名の設定（優先度高）

**目的**: メールにデジタル署名を付与し、改ざんされていないことを証明

**必要な設定**:
- PostfixにDKIMキーを生成・設定
- DNSのTXTレコードに公開鍵を登録（例: `default._domainkey.salesmind.mind-bridge.tech`）

**実装**:
- OpenDKIMなどのツールを使用
- Postfixと連携してメールに署名を付与

#### 3. DMARCポリシーの設定（推奨）

**目的**: SPFとDKIMの結果に基づいてメールの処理方法を指定

**必要な設定**:
- DNSのTXTレコードにDMARCレコードを追加
- 例: `_dmarc.salesmind.mind-bridge.tech` に `v=DMARC1; p=quarantine; rua=mailto:dmarc@salesmind.mind-bridge.tech`

### 実装優先度

1. **SPFレコード**: 最も簡単で効果的。優先的に実装すべき
2. **DKIM署名**: SPFと併用することで信頼性が向上
3. **DMARCポリシー**: SPFとDKIMの後に実装

### 参考リンク

- Gmail SPF設定ガイド: https://support.google.com/mail/answer/81126#authentication
- SPF Record Checker: https://mxtoolbox.com/spf.aspx
- DKIM Record Checker: https://mxtoolbox.com/dkim.aspx

---

## 結論

### ✅ 解決した問題

**Postfixのchroot環境によるDNS解決失敗の問題は完全に解決しました。**

- DNS解決: ✅ 正常に動作
- メールキュー: ✅ 滞留なし
- メールサーバーへの接続: ✅ 成功

### ⚠️ 次の課題

**SPF/DKIM認証の設定が必要です。**

現在、メールはGmailサーバーまで正常に到達しますが、認証が設定されていないため拒否されています。これはDNS解決とは独立した問題であり、メール認証の設定により解決できます。

### 学んだこと

1. **Postfixのchroot動作**: chroot環境内でもDNS解決ができるように、必要なファイルをコピーする必要がある
2. **DockerのDNS**: `/etc/resolv.conf`が`127.0.0.11`のままなのは正常。内部DNSが外部DNSにフォワードする
3. **問題の切り分け**: `dig`コマンドが成功するのにPostfixだけ失敗する場合は、chroot環境を疑うべき

### レポート履歴

- **report01** (`error_report202512.md`): 初期問題（DNS解決失敗）の分析
- **report02** (`report02.md`): chroot DNS fixの適用と問題解決の確認

---

## 補足情報

### 確認コマンド

#### chroot環境内のファイル確認

```bash
docker compose exec mailserver sh -lc '
echo "### chroot etc dir";
ls -la /var/spool/postfix/etc;
echo "### chroot resolv.conf";
cat /var/spool/postfix/etc/resolv.conf || true;
'
```

#### Postfixの設定確認

```bash
docker compose exec mailserver sh -lc '
echo "### queue_directory";
postconf -h queue_directory;
echo "### master.cf smtp lines";
grep -nE "^(smtp|lmtp)\s" /etc/postfix/master.cf || true;
'
```

#### メールキューの確認

```bash
docker compose exec mailserver postqueue -p
```

#### メールログの確認

```bash
docker compose logs -n 100 mailserver | grep -E "smtp|gmail|relay|sent|delivered|250|status="
```

### 関連ファイル

- `mailserver/start.sh`: Postfix起動スクリプト（chroot DNS fix追加済み）
- `docker-compose.yml`: Docker Compose設定（DNS設定含む）
- `backend/spin/models.py`: UserEmailモデル定義
- `backend/spin/admin.py`: 管理者画面の設定
- `backend/spin/email_service.py`: メール送信機能
- `backend/salesmind/settings.py`: Django設定（メール設定含む）



