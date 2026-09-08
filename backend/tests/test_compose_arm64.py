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
    assert "environment:" not in postgres
    assert "url: ${POSTGRES_HOST}:5432" in GRAFANA_DATASOURCE
    assert "database: ${POSTGRES_DB}" in GRAFANA_DATASOURCE
    assert "user: ${POSTGRES_USER}" in GRAFANA_DATASOURCE
    assert "password: ${POSTGRES_PASSWORD}" in GRAFANA_DATASOURCE


def test_all_database_consumers_use_canonical_environment_names():
    runtime_files = [
        ROOT / "docker-compose.yaml",
        ROOT / "backend/disti/repository.py",
        ROOT / "backend/hardware_agent.py",
        ROOT / "backend/migrate.py",
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

    for service in ("postgres", "backend", "hardware-agent", "watchdog"):
        match = re.search(rf"^  {re.escape(service)}:\n(.*?)(?=^  \S|\Z)", BASE_COMPOSE,
                          flags=re.MULTILINE | re.DOTALL)
        assert match is not None
        section = match.group(1)
        assert "- ${DISTI_ENV_FILE:-disti.env}" in section


def test_example_environment_is_safe_and_local_environment_is_ignored():
    example = (ROOT / "disti.env.example").read_text()
    assert "POSTGRES_HOST=postgres" in example
    assert "POSTGRES_DB=postgres" in example
    assert "POSTGRES_USER=postgres" in example
    assert "POSTGRES_PASSWORD=change-me" in example
    assert "DOCKER_POSTGRES_INIT_" not in example
    assert "disti.env" in (ROOT / ".gitignore").read_text().splitlines()


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
def test_compose_config_injects_postgres_environment_without_env_file_flag(tmp_path):
    env_file = tmp_path / "disti.env"
    env_file.write_text((ROOT / "disti.env.example").read_text())
    result = subprocess.run(
        ["docker", "compose", "-f", str(ROOT / "docker-compose.yaml"), "config"],
        cwd=ROOT,
        env=os.environ | {"DISTI_ENV_FILE": str(env_file)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "variable is not set" not in result.stderr
    match = re.search(r"^  postgres:\n(.*?)(?=^  \S|\Z)", result.stdout,
                      flags=re.MULTILINE | re.DOTALL)
    assert match is not None
    postgres = match.group(1)
    assert "POSTGRES_DB: postgres" in postgres
    assert "POSTGRES_HOST: postgres" in postgres
    assert "POSTGRES_USER: postgres" in postgres
    assert "POSTGRES_PASSWORD: change-me" in postgres


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
