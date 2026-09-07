#!/usr/bin/env bash
set -Eeuo pipefail
CONFIG=;REPLACE=false
while (($#));do case "$1" in --config) CONFIG="${2:?}";shift 2;;--replace-config)REPLACE=true;shift;;*)echo "Unknown argument: $1" >&2;exit 1;;esac;done
[[ $EUID -eq 0 && -s $CONFIG ]]||{ echo 'Root and nonempty --config required' >&2;exit 1;}
command -v wg >/dev/null&&command -v wg-quick >/dev/null||{ apt-get update;apt-get install -y wireguard;}
DEST=/etc/wireguard/wg0.conf;install -d -m0700 /etc/wireguard
if [[ -e $DEST ]];then cmp -s "$CONFIG" "$DEST"&&{ echo 'WireGuard configuration already current';exit 0;};$REPLACE||{ echo 'Refusing to replace existing WireGuard configuration' >&2;exit 1;};fi
install -o root -g root -m0600 "$CONFIG" "$DEST";systemctl enable --now wg-quick@wg0;systemctl is-active --quiet wg-quick@wg0
