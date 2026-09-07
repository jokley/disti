#!/usr/bin/env bash
set -Eeuo pipefail
DISTI_USER="${DISTI_USER:-pi}";WG_CONFIG=;REPLACE_WG=false;SKIP_WG=false;KIOSK=true;MODE=auto;MODEM=false;SKIP_DOCKER=false;ROLLOUT=true;BRANCH=main;PROFILE=raspberry;REPLACE_ROLLOUT=false
usage(){ echo "Usage: sudo $0 [--wireguard-config PATH] [--replace-wireguard-config] [--skip-wireguard] [--no-kiosk] [--kiosk-autostart auto|labwc|lxde|xdg] [--usb-modem-recovery] [--skip-docker] [--no-rollout] [--rollout-branch qa|main] [--rollout-compose-profile base|raspberry] [--replace-rollout-config]"; }
while (($#));do case "$1" in -h|--help)usage;exit 0;;--wireguard-config)WG_CONFIG="${2:?}";shift 2;;--replace-wireguard-config)REPLACE_WG=true;shift;;--skip-wireguard)SKIP_WG=true;shift;;--no-kiosk)KIOSK=false;shift;;--kiosk)KIOSK=true;shift;;--kiosk-autostart)MODE="${2:?}";shift 2;;--usb-modem-recovery)MODEM=true;shift;;--skip-docker)SKIP_DOCKER=true;shift;;--no-rollout)ROLLOUT=false;shift;;--rollout)ROLLOUT=true;shift;;--rollout-branch)BRANCH="${2:?}";shift 2;;--rollout-compose-profile)PROFILE="${2:?}";shift 2;;--replace-rollout-config)REPLACE_ROLLOUT=true;shift;;*)echo "Unknown argument: $1" >&2;exit 1;;esac;done
[[ $EUID -eq 0 ]]||{ echo 'Run with sudo'>&2;exit 1;};case "$MODE" in auto|labwc|lxde|xdg);;*)exit 2;;esac;case "$BRANCH" in qa|main);;*)echo 'Automatic rollout allows qa or main only'>&2;exit 2;;esac;case "$PROFILE" in base|raspberry);;*)exit 2;;esac
[[ $SKIP_WG == false || $REPLACE_WG == false ]]||{ echo 'Conflicting WireGuard options'>&2;exit 2;};DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"&&pwd);WG_CONFIG=${WG_CONFIG:-$DIR/client-configs/wg0.conf};export DISTI_USER
if ! $SKIP_DOCKER; then "$DIR/install-docker.sh"; fi
if ! $SKIP_WG;then [[ -s $WG_CONFIG ]]||{ echo "WireGuard configuration missing: $WG_CONFIG" >&2;exit 1;};args=(--config "$WG_CONFIG");$REPLACE_WG&&args+=(--replace-config);"$DIR/setup_wireguard.sh" "${args[@]}";fi
if $KIOSK; then "$DIR/install_piterminal.sh" --autostart "$MODE"; fi
if $MODEM; then "$DIR/setup_internet_check.sh"; fi
if $ROLLOUT;then args=(--branch "$BRANCH" --compose-profile "$PROFILE");$REPLACE_ROLLOUT&&args+=(--replace-config);"$DIR/setup_rollout.sh" "${args[@]}";fi
echo 'DISTI client bootstrap completed; reboot before validating kiosk and Docker group membership.'
