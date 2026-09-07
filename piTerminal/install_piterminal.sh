#!/usr/bin/env bash
set -Eeuo pipefail
DISTI_USER="${DISTI_USER:-pi}";MODE=auto
while (($#));do case "$1" in --autostart)MODE="${2:?}";shift 2;;*)echo "Unknown argument $1" >&2;exit 1;;esac;done
[[ $EUID -eq 0 ]]||{ echo 'Run with sudo' >&2;exit 1;};case "$MODE" in auto|labwc|lxde|xdg);;*)echo 'Invalid autostart mode'>&2;exit 1;;esac
id "$DISTI_USER" >/dev/null;GROUP=$(id -gn "$DISTI_USER");HOME_DIR=$(getent passwd "$DISTI_USER"|cut -d: -f6);DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"&&pwd)
for f in start.sh start-kiosk-loop.sh assets/disti-icon.svg assets/disti-background.svg;do [[ -f $DIR/$f ]]||{ echo "Missing $f" >&2;exit 1;};done
[[ -e /etc/disti-kiosk.conf ]]||cat >/etc/disti-kiosk.conf <<'CFG'
KIOSK_URL="http://127.0.0.1/"
KIOSK_HEALTH_URL="http://127.0.0.1/"
KIOSK_WAIT_TIMEOUT_SEC="300"
CFG
chmod 0644 /etc/disti-kiosk.conf
LABWC="$HOME_DIR/.config/labwc/autostart";LXDE="$HOME_DIR/.config/lxsession/LXDE-pi/autostart";XDG="$HOME_DIR/.config/autostart/disti-kiosk.desktop"
for f in "$LABWC" "$LXDE";do [[ -f $f ]]&&sed -i '\|piTerminal/start-kiosk-loop.sh|d' "$f";done;rm -f "$XDG"
if [[ $MODE == auto ]];then if [[ -d $HOME_DIR/.config/labwc ]];then MODE=labwc;elif [[ -d $HOME_DIR/.config/lxsession/LXDE-pi ]];then MODE=lxde;else MODE=xdg;fi;fi
CMD="$DIR/start-kiosk-loop.sh"
case "$MODE" in labwc)install -d -o "$DISTI_USER" -g "$GROUP" "$(dirname "$LABWC")";echo "$CMD &" >>"$LABWC";chown "$DISTI_USER:$GROUP" "$LABWC";;lxde)install -d -o "$DISTI_USER" -g "$GROUP" "$(dirname "$LXDE")";echo "@$CMD" >>"$LXDE";chown "$DISTI_USER:$GROUP" "$LXDE";;xdg)install -d -o "$DISTI_USER" -g "$GROUP" "$(dirname "$XDG")";cat >"$XDG" <<DESKTOP
[Desktop Entry]
Type=Application
Name=DISTI Kiosk
Exec=$CMD
X-GNOME-Autostart-enabled=true
DESKTOP
chown "$DISTI_USER:$GROUP" "$XDG";;esac
install -d -o "$DISTI_USER" -g "$GROUP" "$HOME_DIR/Desktop";cat >"$HOME_DIR/Desktop/disti.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=DISTI
Exec=$DIR/start.sh
Icon=$DIR/assets/disti-icon.svg
Terminal=false
DESKTOP
chmod 0755 "$HOME_DIR/Desktop/disti.desktop";chown "$DISTI_USER:$GROUP" "$HOME_DIR/Desktop/disti.desktop";rm -f /etc/systemd/system/kiosk.service
