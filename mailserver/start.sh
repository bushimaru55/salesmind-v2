#!/bin/bash

# Postfixの設定
MYHOSTNAME=${POSTFIX_MYHOSTNAME:-mail.salesmind.mind-bridge.tech}
MYDOMAIN=${POSTFIX_MYDOMAIN:-salesmind.mind-bridge.tech}

echo "Configuring Postfix for $MYHOSTNAME / $MYDOMAIN"

# Postfixの基本設定
postconf -e "myhostname = $MYHOSTNAME"
postconf -e "mydomain = $MYDOMAIN"
postconf -e "myorigin = \$mydomain"
postconf -e "inet_interfaces = all"
postconf -e "inet_protocols = ipv4"
postconf -e "mydestination = \$myhostname, localhost.\$mydomain, localhost, \$mydomain"

# ネットワーク設定（Dockerネットワークを許可）
postconf -e "mynetworks = 172.16.0.0/12, 192.168.0.0/16, 10.0.0.0/8, 127.0.0.0/8"

# リレー設定（外部メール送信を許可）
postconf -e "relayhost ="

# セキュリティ設定
postconf -e "smtpd_banner = \$myhostname ESMTP"
postconf -e "disable_vrfy_command = yes"
postconf -e "smtpd_helo_required = yes"

# 受信制限（内部ネットワークからの送信を許可）
postconf -e "smtpd_recipient_restrictions = permit_mynetworks, reject_unauth_destination, permit"

# メールボックス設定
postconf -e "home_mailbox = Maildir/"
postconf -e "mailbox_command ="

# メールサイズ制限（10MB）
postconf -e "message_size_limit = 10485760"
postconf -e "mailbox_size_limit = 0"

# DNS解決設定（MXレコード解決を改善）
postconf -e "smtp_dns_support_level = enabled"
postconf -e "smtp_host_lookup = dns"
postconf -e "smtp_connect_timeout = 30s"

# OpenDKIM milter設定
postconf -e "smtpd_milters = unix:/opendkim/opendkim.sock"
postconf -e "non_smtpd_milters = unix:/opendkim/opendkim.sock"
postconf -e "milter_default_action = accept"
postconf -e "milter_protocol = 6"

# /opendkim へのシンボリックリンクを作成（Postfixのchroot環境用）
ln -sf /var/spool/postfix/opendkim /opendkim || true

# ログをstdoutに出力
postconf -e "maillog_file = /dev/stdout"

# 設定の確認
/usr/sbin/postfix check

echo "Postfix configuration completed"

# DNS設定を確認（docker-compose.ymlで指定されたDNS設定を使用）
echo "DNS設定:"
cat /etc/resolv.conf
echo ""

# DNS解決テスト
echo "DNS解決テスト:"
if command -v host > /dev/null 2>&1; then
    host gmail.com || echo "hostコマンドで解決失敗"
fi

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

# --- rsyslogd 起動（ログ基盤の確保） ---
echo "Starting rsyslogd for proper logging..."
# mail.logの権限を事前に設定
touch /var/log/mail.log
chown syslog:adm /var/log/mail.log
chmod 640 /var/log/mail.log
# rsyslogd起動（imklogエラーは無視：コンテナでは/proc/kmsgにアクセスできないのは正常）
rsyslogd
sleep 1
echo "rsyslogd started"

# --- OpenDKIM 起動確認（存在する場合） ---
if [ -f /etc/opendkim.conf ] && command -v opendkim > /dev/null 2>&1; then
    echo "Starting OpenDKIM..."
    opendkim -x /etc/opendkim.conf
    sleep 1
    echo "OpenDKIM started"
fi

# Postfixをフォアグラウンドで起動（ログはstdoutに出力）
# 注意: DNS設定はdocker-compose.ymlで指定された設定を使用
# DNS設定を変更する場合は、コンテナを再起動する必要がある（postfix reloadでは反映されない）
exec /usr/sbin/postfix start-fg
