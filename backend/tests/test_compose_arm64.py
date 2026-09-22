from pathlib import Path
import os
import re
import stat
import shutil
import subprocess

import pytest

from disti.repository import Repository


ROOT = Path(__file__).resolve().parents[2]
BASE_COMPOSE = (ROOT / "docker-compose.yaml").read_text()
NGINX_CONFIG = (ROOT / "nginx/nginx.conf").read_text()
GRAFANA_DATASOURCE = (ROOT / "grafana/provisioning/datasources/datasources.yaml").read_text()
README = (ROOT / "README.md").read_text()


def test_compose_has_no_legacy_architecture_or_frontend_references():
    combined = BASE_COMPOSE + NGINX_CONFIG

    assert not BASE_COMPOSE.startswith("version:")
    assert "arm32" not in combined
    assert "arm64v8/" not in combined
    assert "jokley/disti-nextjs" not in combined
    assert "next-frontend" not in combined
    assert "location /next/" not in NGINX_CONFIG
    assert "frontend:" not in BASE_COMPOSE
    for legacy in ("flask-backend", "example-network", "mqtt-broker"):
        assert legacy not in combined
    assert "  api:" in BASE_COMPOSE
    assert "container_name: disti-api" in BASE_COMPOSE
    assert "container_name: disti-mqtt" in BASE_COMPOSE
    assert "container_name: disti-grafana" in BASE_COMPOSE
    assert "container_name: disti-nginx" in BASE_COMPOSE
    assert "disti-network" in BASE_COMPOSE


def test_compose_uses_portable_multi_arch_images():
    assert "image: nginx:alpine" in BASE_COMPOSE
    assert "context: ./mosquitto" in BASE_COMPOSE
    assert "image: timescale/timescaledb:latest-pg15" in BASE_COMPOSE
    assert "image: grafana/grafana:13.2.1" in BASE_COMPOSE
    assert BASE_COMPOSE.count("image: disti-backend") == 2


def test_documented_migration_rebuilds_and_uses_running_backend():
    assert "up -d --build postgres api" in README
    assert "exec -T api python -m entrypoints.migrate" in README
    assert "run --rm api python -m entrypoints.migrate" not in README


def test_postgres_compose_uses_canonical_device_environment():
    postgres = BASE_COMPOSE.split("  mqtt:", 1)[0]

    assert "- disti.env" in postgres
    assert "environment:" not in postgres
    assert "url: ${POSTGRES_HOST}:5432" in GRAFANA_DATASOURCE
    assert "database: ${POSTGRES_DB}" in GRAFANA_DATASOURCE
    assert "user: ${POSTGRES_USER}" in GRAFANA_DATASOURCE
    assert "password: ${POSTGRES_PASSWORD}" in GRAFANA_DATASOURCE


def test_all_database_consumers_use_canonical_environment_names():
    runtime_files = [
        ROOT / "docker-compose.yaml",
        ROOT / "backend/disti/repository.py",
        ROOT / "backend/entrypoints/hardware_agent.py",
        ROOT / "backend/entrypoints/migrate.py",
        ROOT / "watchdog/watchdog.py",
        ROOT / "grafana/provisioning/datasources/datasources.yaml",
        ROOT / "piTerminal/rollout/disti-update",
        ROOT / "piTerminal/setup_rollout.sh",
    ]
    combined = "\n".join(path.read_text() for path in runtime_files)
    assert "DOCKER_POSTGRES_INIT_USERNAME" not in combined
    assert "DOCKER_POSTGRES_INIT_PASSWORD" not in combined
    for name in ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        assert name in combined
        assert f'os.getenv("{name}",' not in combined

    for service in ("postgres", "mqtt", "api", "hardware-agent", "watchdog", "grafana"):
        match = re.search(rf"^  {re.escape(service)}:\n(.*?)(?=^  \S|\Z)", BASE_COMPOSE,
                          flags=re.MULTILINE | re.DOTALL)
        assert match is not None
        section = match.group(1)
        assert "- disti.env" in section


def test_example_environment_is_safe_and_local_environment_is_ignored():
    example = (ROOT / "disti.env.example").read_text()
    assert "POSTGRES_HOST=postgres" in example
    assert "POSTGRES_DB=jokley" in example
    assert "POSTGRES_USER=jokley" in example
    assert "POSTGRES_PASSWORD=change-me" in example
    canonical = {
        "POSTGRES_HOST": "postgres",
        "POSTGRES_DB": "jokley",
        "POSTGRES_USER": "jokley",
        "POSTGRES_PASSWORD": "change-me",
        "GF_SECURITY_ADMIN_USER": "jokley",
        "GF_SECURITY_ADMIN_PASSWORD": "change-me",
        "MQTT_USERNAME": "jokley",
        "MQTT_PASSWORD": "change-me",
        "DISTI_HARDWARE_MODE": "mock",
        "DISTI_POLL_INTERVAL_SECONDS": "2",
        "DISTI_HARDWARE_HEALTH_PORT": "8081",
        "DISTI_HARDWARE_HEALTH_URL": "http://hardware-agent:8081",
        "DISTI_HARDWARE_MAX_AGE_SEC": "30",
        "DISTI_ADC_TYPE": "ads1115",
        "DISTI_I2C_BUS": "1",
        "DISTI_ADS1115_ADDRESS": "0x48",
        "DISTI_ADS1115_EC_CHANNEL": "0",
        "DISTI_ADS1115_PT1000_CHANNEL": "1",
        "DISTI_ADS1115_GAIN": "1",
        "DISTI_ADS1115_DATA_RATE": "128",
        "DISTI_ONEWIRE_TYPE": "ds2484",
        "DISTI_DS2484_I2C_BUS": "1",
        "DISTI_DS2484_ADDRESS": "0x18",
        "DISTI_ONEWIRE_VAPOR_ID": "",
        "DISTI_ONEWIRE_COOLER_ID": "",
        "DISTI_ONEWIRE_RESERVE_ID": "",
        "DISTI_NTFY_ENABLED": "false",
        "DISTI_NTFY_BASE_URL": "https://ntfy.sh",
        "DISTI_NTFY_TOPIC": "",
        "WATCHDOG_CHECK_INTERVAL_SEC": "30",
        "WATCHDOG_BACKEND_RECHECK_SEC": "2",
        "WATCHDOG_RECOVERY_WAIT_SEC": "30",
        "WATCHDOG_COOLDOWN_SEC": "120",
        "WATCHDOG_MAX_RESTARTS_PER_HOUR": "4",
        "WATCHDOG_BACKEND_RETRIES": "3",
        "WATCHDOG_ALERT_COOLDOWN_SEC": "900",
        "DISTI_REPLAY_RUN_ID": "",
        "DISTI_REPLAY_SPEED": "1",
        "DISTI_REPLAY_PRESERVE_TIMING": "true",
    }
    values = dict(line.split("=", 1) for line in example.splitlines()
                  if line and not line.startswith("#"))
    assert values == canonical
    assert set(values.values()) <= {"postgres", "jokley", "change-me", "mock", "2", "8081",
                                    "http://hardware-agent:8081", "30", "120", "4", "3", "900",
                                    "", "0", "0x48", "0x18", "ads1115", "ds2484",
                                    "128", "1", "true", "false", "https://ntfy.sh"}
    ignored = (ROOT / ".gitignore").read_text().splitlines()
    for path in ("disti.env", ".env", ".disti-local/", "mosquitto/password.txt",
                 "nginx/.htpasswd", "piTerminal/client-configs/"):
        assert path in ignored
    assert not (ROOT / ".env.example").exists()
    assert subprocess.run(["git", "check-ignore", "--quiet", "disti.env"], cwd=ROOT).returncode == 0
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, text=True,
                             capture_output=True, check=True).stdout.splitlines()
    assert "disti.env.example" in tracked
    assert ".env.example" not in tracked



def test_compose_has_no_credential_interpolation_or_legacy_names():
    legacy_names = (
        "DOCKER_POSTGRES_INIT_USERNAME", "DOCKER_POSTGRES_INIT_PASSWORD",
        "DOCKER_GRAFANA_INIT_USERNAME", "DOCKER_GRAFANA_INIT_PASSWORD",
        "DOCKER_MQTT_INIT_USERNAME", "DOCKER_MQTT_INIT_PASSWORD",
    )
    runtime_files = [
        ROOT / "docker-compose.yaml", ROOT / "disti.env.example",
        ROOT / "mosquitto/docker-entrypoint-disti.sh",
        ROOT / "piTerminal/setup_rollout.sh", ROOT / "piTerminal/rollout/disti-update",
    ]
    combined = "\n".join(path.read_text() for path in runtime_files)
    assert all(name not in combined for name in legacy_names)
    assert "DISTI_ENV_FILE" not in combined
    assert not re.search(r"\$\{[^}]*?(?:PASSWORD|USERNAME|USER)[^}]*}", BASE_COMPOSE)
    assert "GF_SECURITY_ADMIN_USER" not in BASE_COMPOSE.split("environment:")[-1]


def test_repository_requires_explicit_postgres_configuration(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for name in ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        Repository.from_environment()

    message = str(exc_info.value)
    assert message.startswith("Missing required PostgreSQL configuration:")
    for name in ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        assert name in message


def test_repository_passes_explicit_postgres_configuration(monkeypatch):
    values = {
        "POSTGRES_HOST": "database.internal",
        "POSTGRES_DB": "disti_qa",
        "POSTGRES_USER": "hardware_agent",
        "POSTGRES_PASSWORD": "device-secret",
    }
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    captured = {}
    monkeypatch.setattr(
        "disti.repository.psycopg2.connect",
        lambda **kwargs: captured.update(kwargs),
    )

    Repository.from_environment().connection_factory()

    assert captured == {
        "host": values["POSTGRES_HOST"],
        "database": values["POSTGRES_DB"],
        "user": values["POSTGRES_USER"],
        "password": values["POSTGRES_PASSWORD"],
        "port": "5432",
    }


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker Compose unavailable")
def test_compose_config_injects_root_environment_without_env_file_flag(tmp_path):
    compose = tmp_path / "docker-compose.yaml"
    compose.write_text(BASE_COMPOSE)
    (tmp_path / "disti.env").write_text((ROOT / "disti.env.example").read_text())
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose), "config"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "variable is not set" not in result.stderr
    match = re.search(r"^  postgres:\n(.*?)(?=^  \S|\Z)", result.stdout,
                      flags=re.MULTILINE | re.DOTALL)
    assert match is not None
    postgres = match.group(1)
    assert "POSTGRES_DB: jokley" in postgres
    assert "POSTGRES_HOST: postgres" in postgres
    assert "POSTGRES_USER: jokley" in postgres
    assert "POSTGRES_PASSWORD: change-me" in postgres
    grafana = re.search(r"^  grafana:\n(.*?)(?=^  \S|\Z)", result.stdout,
                        flags=re.MULTILINE | re.DOTALL).group(1)
    assert "GF_SECURITY_ADMIN_USER: jokley" in grafana
    assert "GF_SECURITY_ADMIN_PASSWORD: change-me" in grafana


def test_mqtt_credentials_generate_an_untracked_password_file_at_startup():
    entrypoint = (ROOT / "mosquitto/docker-entrypoint-disti.sh").read_text()
    mosquitto_config = (ROOT / "mosquitto/mosquitto.conf").read_text()

    assert "env_file:" in BASE_COMPOSE
    assert "MQTT_USERNAME" in entrypoint
    assert "MQTT_PASSWORD" in entrypoint
    assert "mosquitto_passwd -b \"$temporary_file\"" in entrypoint
    assert "mosquitto_passwd -b -c" not in entrypoint
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
    passwd.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        "[ \"$1\" = '-b' ]\n"
        "[ \"${2:-}\" != '-c' ]\n"
        "[ -f \"$2\" ]\n"
        "printf '%s\\n' '$7$hashed-not-plaintext' > \"$2\"\n"
    )
    passwd.chmod(0o755)
    env = os.environ | {
        "PATH": f"{binaries}:{os.environ['PATH']}",
        "MQTT_USERNAME": "qa-user",
        "MQTT_PASSWORD": "plaintext-secret",
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
    service_config = BASE_COMPOSE.split("\nnetworks:", 1)[0]
    service_matches = re.findall(r"^  ([\w-]+):\n(.*?)(?=^  \S|\Z)", service_config,
                                 flags=re.MULTILINE | re.DOTALL)
    services = dict(service_matches)
    expected = {"api", "hardware-agent", "postgres", "mqtt", "watchdog", "grafana", "nginx"}

    assert set(services) == expected
    assert {re.search(r"^    container_name: (.+)$", config, re.MULTILINE).group(1)
            for config in services.values()} == {
        "disti-api", "disti-hardware-agent", "disti-postgres", "disti-mqtt",
        "disti-watchdog", "disti-grafana", "disti-nginx",
    }
    hardware_agent = services["hardware-agent"]
    assert "DISTI_HARDWARE_MODE: raspberry" in hardware_agent
    assert hardware_agent.count("/dev/i2c-1:/dev/i2c-1") == 1
    assert all("/dev/i2c-1" not in config for name, config in services.items()
               if name != "hardware-agent")
    assert all("privileged:" not in config for config in services.values())
    assert "image: disti-backend" in services["api"]
    assert "image: disti-backend" in hardware_agent
    assert "healthcheck:" in services["api"]
    assert "healthcheck:" in hardware_agent
    watchdog = services["watchdog"]
    assert "WATCHDOG_BACKEND_CONTAINER: disti-api" in watchdog
    assert "WATCHDOG_HARDWARE_CONTAINER: disti-hardware-agent" in watchdog
    assert "WATCHDOG_DATABASE_CONTAINER: disti-postgres" in watchdog


def test_runtime_structure_and_grafana_have_no_removed_legacy_dependencies():
    tracked_runtime = "\n".join(
        (ROOT / path).read_text(errors="ignore")
        for path in ("docker-compose.yaml", "disti.env.example", "README.md",
                     "grafana/provisioning/datasources/datasources.yaml")
    ).lower()
    assert not (ROOT / "influxdb").exists()
    assert not (ROOT / "telegraf").exists()
    assert "influxdb" not in tracked_runtime
    assert "telegraf" not in tracked_runtime
    assert "type: postgres" in GRAFANA_DATASOURCE
    assert "timescaledb: true" in GRAFANA_DATASOURCE
    assert (ROOT / "backend/entrypoints/api.py").exists()
    assert (ROOT / "backend/entrypoints/hardware_agent.py").exists()
