#!/bin/sh
set -eu

: "${DOCKER_MQTT_INIT_USERNAME:?DOCKER_MQTT_INIT_USERNAME must be set in .env}"
: "${DOCKER_MQTT_INIT_PASSWORD:?DOCKER_MQTT_INIT_PASSWORD must be set in .env}"

password_dir=/run/mosquitto
password_file="$password_dir/password.txt"
runtime_user=mosquitto
runtime_uid="$(id -u "$runtime_user")"
runtime_gid="$(id -g "$runtime_user")"
umask 077
mkdir -p "$password_dir"
chown "$runtime_uid:$runtime_gid" "$password_dir"
chmod 0750 "$password_dir"

# /run survives a restart of the same container. Generate into a unique file so
# neither the final file nor a stale interrupted attempt can make startup fail.
find "$password_dir" -maxdepth 1 -type f -name '.password.txt.*' -delete
temporary_file="$(mktemp "$password_dir/.password.txt.XXXXXX")"
trap 'rm -f "$temporary_file"' EXIT HUP INT TERM
mosquitto_passwd -b -c "$temporary_file" \
  "$DOCKER_MQTT_INIT_USERNAME" "$DOCKER_MQTT_INIT_PASSWORD"
chown "$runtime_uid:$runtime_gid" "$temporary_file"
chmod 0600 "$temporary_file"
mv -f "$temporary_file" "$password_file"
trap - EXIT HUP INT TERM

exec /docker-entrypoint.sh "$@"
