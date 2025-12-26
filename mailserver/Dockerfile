FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Postfixと必要なパッケージをインストール（rsyslog, opendkimを追加）
RUN apt-get update && \
    apt-get install -y postfix mailutils rsyslog dnsutils opendkim opendkim-tools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Postfixの起動スクリプト
COPY start.sh /start.sh
RUN chmod +x /start.sh

# OpenDKIM設定ファイルとキーをコピー
COPY opendkim/opendkim.conf /etc/opendkim.conf
COPY opendkim/KeyTable /etc/opendkim/KeyTable
COPY opendkim/SigningTable /etc/opendkim/SigningTable
COPY opendkim/TrustedHosts /etc/opendkim/TrustedHosts
COPY opendkim/keys /etc/opendkim/keys

# OpenDKIMの権限設定
RUN mkdir -p /var/spool/postfix/opendkim && \
    chown -R opendkim:opendkim /etc/opendkim && \
    chown -R opendkim:postfix /etc/opendkim/KeyTable /etc/opendkim/SigningTable /etc/opendkim/TrustedHosts && \
    chmod 644 /etc/opendkim/KeyTable /etc/opendkim/SigningTable /etc/opendkim/TrustedHosts && \
    chown opendkim:opendkim /etc/opendkim/keys/salesmind.mind-bridge.tech/s1.private && \
    chmod 0400 /etc/opendkim/keys/salesmind.mind-bridge.tech/s1.private && \
    chown opendkim:postfix /var/spool/postfix/opendkim && \
    chmod 750 /var/spool/postfix/opendkim

EXPOSE 25 587 465

CMD ["/start.sh"]

