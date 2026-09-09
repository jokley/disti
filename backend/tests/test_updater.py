from pathlib import Path
import os
import subprocess


def test_update_scripts_restrict_channels_and_use_fast_forward():
    root = Path(__file__).parents[2]
    status = (root / "scripts/update-status.sh").read_text()
    update = (root / "piTerminal/rollout/disti-update").read_text()
    assert "qa|main" in status and "qa|main" in update
    assert "dev|qa|main" not in status + update
    assert "flock -n" in update
    assert "git reset --hard" in update
    assert "config --quiet" in update
    assert "pull --ignore-buildable" in update
    assert "--remove-orphans --wait --wait-timeout" in update
    assert "CRITICAL: rollback failed" in update


def test_provisioning_defaults_to_main_and_installs_stable_runtime():
    root = Path(__file__).parents[2]
    setup = (root / "piTerminal/setup_rollout.sh").read_text()
    client = (root / "piTerminal/setup_client.sh").read_text()
    assert "DEPLOY_BRANCH=main" in setup
    assert "BRANCH=main" in client
    assert "/etc/disti-update.conf" in setup
    assert "/usr/local/sbin/disti-update" in setup
    assert "--compose-profile" in setup
    assert "base|raspberry" in setup
    assert 'install -o "$DISTI_USER" -g "$GROUP" -m0600 "$REPO_DIR/disti.env.example" "$REPO_DIR/disti.env"' in setup
    assert ".disti-local" not in setup
    assert "DISTI_MQTT_PASSWORD_FILE" not in setup


def test_rollout_requires_disti_env_without_compose_override():
    root = Path(__file__).parents[2]
    updater = (root / "piTerminal/rollout/disti-update").read_text()

    assert '[[ -r "$DISTI_DIR/disti.env" ]]' in updater
    assert "COMPOSE_ARGS=(-f docker-compose.yaml)" in updater
    assert "--env-file" not in updater
    assert "git clean" not in updater


def test_runtime_rejects_dev_before_git_or_docker(tmp_path):
    root = Path(__file__).parents[2]
    config = tmp_path / "disti-update.conf"
    config.write_text(f'DISTI_DIR="{tmp_path}"\nDEPLOY_BRANCH="dev"\nCOMPOSE_PROFILE="base"\nHEALTH_URL="http://invalid"\n')
    result = subprocess.run([root / "piTerminal/rollout/disti-update"], text=True,
                            env={**os.environ, "DISTI_UPDATE_CONFIG": str(config),
                                 "DISTI_UPDATE_LOCK": str(tmp_path / "lock")}, capture_output=True)
    assert result.returncode != 0
    assert "allowed: qa, main" in result.stderr


def test_pull_failure_rolls_back_and_revalidates_health(tmp_path):
    root = Path(__file__).parents[2]
    config = tmp_path / "config"
    env_file = tmp_path / "disti.env"
    env_file.write_text("MQTT_USERNAME=test\nMQTT_PASSWORD=test\n")
    config.write_text(f'DISTI_DIR="{tmp_path}"\nDEPLOY_BRANCH="qa"\nCOMPOSE_PROFILE="base"\nHEALTH_URL="http://healthz"\nHEALTH_RETRIES="1"\nHEALTH_SLEEP_SEC="0"\n')
    bindir = tmp_path / "bin"; bindir.mkdir(); log = tmp_path / "calls"
    (bindir / "git").write_text(f'''#!/bin/sh
echo "git $*" >>"{log}"
case "$*" in "rev-parse --is-inside-work-tree") echo true;; "rev-parse HEAD") echo local;; "rev-parse origin/qa") echo remote;; esac
exit 0
''')
    (bindir / "docker").write_text(f'''#!/bin/sh
echo "docker $*" >>"{log}"
case "$*" in *" pull --ignore-buildable") exit 1;; esac
exit 0
''')
    (bindir / "curl").write_text(f'#!/bin/sh\necho "curl $*" >>"{log}"\nexit 0\n')
    for command in ("git", "docker", "curl"):
        (bindir / command).chmod(0o755)
    result = subprocess.run([root / "piTerminal/rollout/disti-update"], text=True,
                            env={**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}",
                                 "DISTI_UPDATE_CONFIG": str(config), "DISTI_UPDATE_LOCK": str(tmp_path / "lock")}, capture_output=True)
    calls = log.read_text()
    assert result.returncode != 0
    assert "git reset --hard remote" in calls
    assert "git reset --hard local" in calls
    assert calls.count("config --quiet") == 2
    assert "curl --fail --silent --show-error --max-time 10 http://healthz" in calls
