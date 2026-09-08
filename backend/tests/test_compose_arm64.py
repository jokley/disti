from pathlib import Path
import os
import stat
import subprocess


ROOT = Path(__file__).resolve().parents[2]
BASE_COMPOSE = (ROOT / "docker-compose.yaml").read_text()
RASPBERRY_COMPOSE = (ROOT / "docker-compose.raspberry.yaml").read_text()
NGINX_CONFIG = (ROOT / "nginx/nginx.conf").read_text()
GRAFANA_DATASOURCE = (ROOT / "grafana/provisioning/datasources/datasources.yaml").read_text()
README = (ROOT / "README.md").read_text()


def test_compose_has_no_legacy_architecture_or_frontend_references():
    combined = BASE_COMPOSE + RASPBERRY_COMPOSE + NGINX_CONFIG

    assert not BASE_COMPOSE.startswith("version:")
    assert "arm32" not in combined
    assert "arm64v8/" not in combined
    assert "jokley/disti-nextjs" not in combined
    assert "next-frontend" not in combined
    assert "location /next/" not in NGINX_CONFIG
    assert "frontend:" not in BASE_COMPOSE


def test_compose_uses_portable_multi_arch_images():
    assert "image: nginx:alpine" in BASE_COMPOSE
    assert "context: ./mosquitto" in BASE_COMPOSE
    assert "image: timescale/timescaledb:latest-pg15" in BASE_COMPOSE
    assert "image: grafana/grafana:9.2.3" in BASE_COMPOSE
    assert BASE_COMPOSE.count("image: disti-backend") == 2


def test_documented_migration_rebuilds_and_uses_running_backend():
    assert "up -d --build postgres backend" in README
    assert "exec -T backend python migrate.py" in README
    assert "run --rm backend python migrate.py" not in README


def test_postgres_compose_uses_canonical_device_environment():
    postgres = BASE_COMPOSE.split("  mqtt:", 1)[0]

    assert "- ${DISTI_ENV_FILE:-disti.env}" in postgres
    assert "POSTGRES_USER: ${DOCKER_POSTGRES_INIT_USERNAME}" in postgres
    assert "POSTGRES_PASSWORD: ${DOCKER_POSTGRES_INIT_PASSWORD}" in postgres
    assert "POSTGRES_DB: ${POSTGRES_DB}" in postgres
    assert "POSTGRES_USER=postgres" not in postgres
    assert "POSTGRES_PASSWORD=postgres" not in postgres
    assert "POSTGRES_DB=postgres" not in postgres
    assert "url: ${POSTGRES_HOST}:5432" in GRAFANA_DATASOURCE
    assert "database: ${POSTGRES_DB}" in GRAFANA_DATASOURCE


def test_mqtt_credentials_generate_an_untracked_password_file_at_startup():
    entrypoint = (ROOT / "mosquitto/docker-entrypoint-disti.sh").read_text()
    mosquitto_config = (ROOT / "mosquitto/mosquitto.conf").read_text()

    assert "env_file:" in BASE_COMPOSE
    assert "DOCKER_MQTT_INIT_USERNAME" in entrypoint
    assert "DOCKER_MQTT_INIT_PASSWORD" in entrypoint
    assert "mosquitto_passwd -b -c \"$temporary_file\"" in entrypoint
    assert "mktemp" in entrypoint
    assert "mv -f \"$temporary_file\" \"$password_file\"" in entrypoint
    assert 'id -u "$runtime_user"' in entrypoint
    assert 'id -g "$runtime_user"' in entrypoint
    assert "chmod 0600 \"$temporary_file\"" in entrypoint
    assert "allow_anonymous false" in mosquitto_config
    assert "password_file /run/mosquitto/password.txt" in mosquitto_config
    assert "DISTI_MQTT_PASSWORD_FILE" not in BASE_COMPOSE
    assert "nginx/.htpasswd" not in BASE_COMPOSE


def test_mqtt_password_initialization_is_restart_safe_and_does_not_leak(tmp_path):
    source = (ROOT / "mosquitto/docker-entrypoint-disti.sh").read_text()
    runtime = tmp_path / "run"
    upstream = tmp_path / "upstream"
    upstream.write_text("#!/bin/sh\nexit 0\n")
    upstream.chmod(0o755)
    script = tmp_path / "entrypoint"
    script.write_text(
        source.replace("password_dir=/run/mosquitto", f"password_dir={runtime}")
        .replace("runtime_user=mosquitto", f"runtime_user={os.getuid()}")
        .replace("exec /docker-entrypoint.sh", f"exec {upstream}")
    )
    script.chmod(0o755)
    binaries = tmp_path / "bin"
    binaries.mkdir()
    passwd = binaries / "mosquitto_passwd"
    passwd.write_text("#!/bin/sh\nprintf '%s\\n' '$7$hashed-not-plaintext' > \"$3\"\n")
    passwd.chmod(0o755)
    env = os.environ | {
        "PATH": f"{binaries}:{os.environ['PATH']}",
        "DOCKER_MQTT_INIT_USERNAME": "qa-user",
        "DOCKER_MQTT_INIT_PASSWORD": "plaintext-secret",
    }

    first = subprocess.run([script], env=env, text=True, capture_output=True)
    assert first.returncode == 0
    password_file = runtime / "password.txt"
    assert password_file.read_text() == "$7$hashed-not-plaintext\n"
    assert stat.S_IMODE(password_file.stat().st_mode) == 0o600
    assert "plaintext-secret" not in first.stdout + first.stderr + password_file.read_text()

    (runtime / ".password.txt.interrupted").write_text("stale")
    second = subprocess.run([script], env=env, text=True, capture_output=True)
    assert second.returncode == 0
    assert password_file.read_text() == "$7$hashed-not-plaintext\n"
    assert not (runtime / ".password.txt.interrupted").exists()
    assert stat.S_IMODE(password_file.stat().st_mode) == 0o600
    assert "plaintext-secret" not in second.stdout + second.stderr


def test_raspberry_device_access_is_hardware_agent_only():
    assert "DISTI_HARDWARE_MODE: raspberry" in RASPBERRY_COMPOSE
    assert RASPBERRY_COMPOSE.count("/dev/i2c-1:/dev/i2c-1") == 1
    assert RASPBERRY_COMPOSE.splitlines()[2].strip() == "hardware-agent:"
    assert "privileged:" not in BASE_COMPOSE + RASPBERRY_COMPOSE
