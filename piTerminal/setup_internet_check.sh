#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]]||{ echo 'Run with sudo'>&2;exit 1;};DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"&&pwd)
install -o root -g root -m0755 "$DIR/internet-check" /usr/local/sbin/disti-internet-check
install -o root -g root -m0644 "$DIR/disti-internet-check.service" /etc/systemd/system/disti-internet-check.service
install -o root -g root -m0644 "$DIR/disti-internet-check.timer" /etc/systemd/system/disti-internet-check.timer
[[ -e /etc/disti-internet-check.conf ]]||cat >/etc/disti-internet-check.conf <<'CFG'
PING_TARGET="1.1.1.1"
USB_VENDOR_ID="12d1"
USB_PRODUCT_ID="14db"
RECOVERY_WAIT_SEC="15"
WIREGUARD_UNIT="wg-quick@wg0"
CFG
chmod 0644 /etc/disti-internet-check.conf;systemctl daemon-reload;systemctl enable --now disti-internet-check.timer
