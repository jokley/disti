from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE_COMPOSE = (ROOT / "docker-compose.yaml").read_text()
RASPBERRY_COMPOSE = (ROOT / "docker-compose.raspberry.yaml").read_text()
NGINX_CONFIG = (ROOT / "nginx/nginx.conf").read_text()


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


def test_mqtt_credentials_generate_an_untracked_password_file_at_startup():
    entrypoint = (ROOT / "mosquitto/docker-entrypoint-disti.sh").read_text()
    mosquitto_config = (ROOT / "mosquitto/mosquitto.conf").read_text()

    assert "env_file:" in BASE_COMPOSE
    assert "DOCKER_MQTT_INIT_USERNAME" in entrypoint
    assert "DOCKER_MQTT_INIT_PASSWORD" in entrypoint
    assert "mosquitto_passwd -b -c" in entrypoint
    assert "chmod 0600" in entrypoint
    assert "allow_anonymous false" in mosquitto_config
    assert "password_file /run/mosquitto/password.txt" in mosquitto_config
    assert "DISTI_MQTT_PASSWORD_FILE" not in BASE_COMPOSE
    assert "nginx/.htpasswd" not in BASE_COMPOSE


def test_raspberry_device_access_is_hardware_agent_only():
    assert "DISTI_HARDWARE_MODE: raspberry" in RASPBERRY_COMPOSE
    assert RASPBERRY_COMPOSE.count("/dev/i2c-1:/dev/i2c-1") == 1
    assert RASPBERRY_COMPOSE.splitlines()[2].strip() == "hardware-agent:"
    assert "privileged:" not in BASE_COMPOSE + RASPBERRY_COMPOSE
