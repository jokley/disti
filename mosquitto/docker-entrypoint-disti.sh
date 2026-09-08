#!/bin/sh
set -eu

: "${DOCKER_MQTT_INIT_USERNAME:?DOCKER_MQTT_INIT_USERNAME must be set in disti.env}"
: "${DOCKER_MQTT_INIT_PASSWORD:?DOCKER_MQTT_INIT_PASSWORD must be set in disti.env}"

password_dir=/run/mosquitto
password_file="$password_dir/password.txt"
umask 077
mkdir -p "$password_dir"
mosquitto_passwd -b -c "$password_file" \
  "$DOCKER_MQTT_INIT_USERNAME" "$DOCKER_MQTT_INIT_PASSWORD"
chmod 0600 "$password_file"

exec /docker-entrypoint.sh "$@"
