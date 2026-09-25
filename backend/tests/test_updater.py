from pathlib import Path
import os
import shutil
import subprocess

import pytest

ROOT = Path(__file__).parents[2]
UPDATER = ROOT / "piTerminal/rollout/disti-update"
SETUP = ROOT / "piTerminal/setup_rollout.sh"
CLIENT = ROOT / "piTerminal/setup_client.sh"


def run(*args, cwd=None, env=None, check=True):
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, check=check)


def git(cwd, *args):
    return run("git", *args, cwd=cwd).stdout.strip()


@pytest.fixture
def rollout(tmp_path):
    remote = tmp_path / "remote.git"
    source = tmp_path / "source"
    device = tmp_path / "device"
    git(tmp_path, "init", "--bare", str(remote))
    git(tmp_path, "init", str(source))
    git(source, "config", "user.email", "test@example.invalid")
    git(source, "config", "user.name", "DISTI test")
    (source / "piTerminal/rollout").mkdir(parents=True)
    (source / "docker-compose.yaml").write_text("services: {}\n")
    (source / "disti.env").write_bytes(b"SECRET=old-device-value\nRAW=\\xff\n")
    (source / "piTerminal/rollout/disti-update").write_text("old updater\n")
    git(source, "add", ".")
    git(source, "commit", "-m", "old tracked environment")
    git(source, "branch", "-M", "qa")
    git(source, "remote", "add", "origin", str(remote))
    git(source, "push", "-u", "origin", "qa")
    old = git(source, "rev-parse", "HEAD")
    git(tmp_path, "clone", "-b", "qa", str(remote), str(device))

    (source / ".gitignore").write_text("disti.env\n")
    git(source, "rm", "disti.env")
    shutil.copy2(UPDATER, source / "piTerminal/rollout/disti-update")
    (source / "version").write_text("new\n")
    git(source, "add", ".")
    git(source, "commit", "-m", "new ignored environment")
    git(source, "push", "origin", "qa")
    new = git(source, "rev-parse", "HEAD")

    bindir = tmp_path / "bin"
    bindir.mkdir()
    calls = tmp_path / "calls"
    docker = bindir / "docker"
    docker.write_text(f'''#!/bin/sh
echo "docker $*" >>"{calls}"
case "$*" in *" ${{DOCKER_FAIL_ON:-never}}"*) exit 1;; esac
''')
    curl = bindir / "curl"
    curl.write_text(f'''#!/bin/sh
echo "curl $*" >>"{calls}"
[ "${{HEALTH_FAIL:-0}}" != 1 ]
''')
    docker.chmod(0o755)
    curl.chmod(0o755)
    config = tmp_path / "disti-update.conf"
    config.write_text(f'''DISTI_DIR="{device}"
DEPLOY_BRANCH="qa"
HEALTH_URL="http://healthz"
HEALTH_RETRIES="1"
HEALTH_SLEEP_SEC="0"
COMPOSE_WAIT_TIMEOUT_SEC="5"
''')
    runtime = tmp_path / "installed-update"
    runtime.write_text("installed old updater\n")
    runtime.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "DISTI_UPDATE_CONFIG": str(config),
        "DISTI_UPDATE_LOCK": str(tmp_path / "lock"),
        "DISTI_UPDATE_RUNTIME": str(runtime),
    }
    return {"device": device, "config": config, "calls": calls, "env": env,
            "old": old, "new": new, "runtime": runtime, "source": source}


def invoke(case, **extra_env):
    return run(UPDATER, env={**case["env"], **extra_env}, check=False)


def test_fresh_qa_and_main_installation_configuration():
    setup = SETUP.read_text()
    client = CLIENT.read_text()
    assert "DEPLOY_BRANCH=main" in setup and "BRANCH=main" in client
    assert "qa|main" in setup and "qa|main" in client
    assert 'install -o "$DISTI_USER" -g "$GROUP" -m0600' in setup
    assert '"$REPO_DIR/.disti-local/disti.env"' in setup
    assert "COMPOSE_PROFILE" not in setup


def test_old_config_without_profile_and_single_compose_rolls_out(rollout):
    result = invoke(rollout)
    assert result.returncode == 0, result.stderr + result.stdout
    calls = rollout["calls"].read_text()
    assert "docker compose -f docker-compose.yaml config --quiet" in calls
    assert "docker-compose.raspberry.yaml" not in calls
    assert "COMPOSE_PROFILE" not in rollout["config"].read_text()


def test_legacy_profile_is_ignored_not_required(rollout):
    with rollout["config"].open("a") as stream:
        stream.write('COMPOSE_PROFILE="raspberry"\n')
    result = invoke(rollout)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "docker-compose.raspberry.yaml" not in rollout["calls"].read_text()


def test_legacy_disti_env_file_is_migrated_to_canonical_root(rollout):
    legacy = rollout["device"] / ".disti-local/disti.env"
    legacy.parent.mkdir()
    legacy.write_bytes(b"SECRET=legacy-local\n")
    (rollout["device"] / "disti.env").unlink()
    with rollout["config"].open("a") as stream:
        stream.write(f'DISTI_ENV_FILE="{legacy}"\n')
    result = invoke(rollout)
    assert result.returncode == 0, result.stderr + result.stdout
    assert (rollout["device"] / "disti.env").read_bytes() == legacy.read_bytes()
    assert "Migrating legacy device configuration" in result.stdout


def test_tracked_to_ignored_environment_survives_byte_for_byte(rollout):
    expected = (rollout["device"] / "disti.env").read_bytes()
    result = invoke(rollout)
    assert result.returncode == 0, result.stderr + result.stdout
    assert git(rollout["device"], "rev-parse", "HEAD") == rollout["new"]
    assert (rollout["device"] / "disti.env").read_bytes() == expected
    assert git(rollout["device"], "check-ignore", "disti.env") == "disti.env"


def test_untracked_environment_survives_future_success(rollout):
    assert invoke(rollout).returncode == 0
    local = rollout["device"] / "disti.env"
    local.write_bytes(b"SECRET=future-local\nspaces = stay exactly\n")
    (rollout["source"] / "version").write_text("newer\n")
    git(rollout["source"], "add", "version")
    git(rollout["source"], "commit", "-m", "another release")
    git(rollout["source"], "push", "origin", "qa")
    expected = local.read_bytes()
    assert invoke(rollout).returncode == 0
    assert local.read_bytes() == expected


def test_failed_health_rolls_back_and_preserves_environment(rollout):
    expected = (rollout["device"] / "disti.env").read_bytes()
    result = invoke(rollout, HEALTH_FAIL="1")
    assert result.returncode != 0
    assert git(rollout["device"], "rev-parse", "HEAD") == rollout["old"]
    assert (rollout["device"] / "disti.env").read_bytes() == expected
    calls = rollout["calls"].read_text()
    assert calls.count("config --quiet") == 2
    assert "Rolling back" in result.stdout


def test_untracked_environment_survives_failed_future_rollout(rollout):
    assert invoke(rollout).returncode == 0
    local = rollout["device"] / "disti.env"
    local.write_bytes(b"SECRET=untracked-before-failure\n")
    expected = local.read_bytes()
    previous = git(rollout["device"], "rev-parse", "HEAD")
    (rollout["source"] / "version").write_text("bad release\n")
    git(rollout["source"], "add", "version")
    git(rollout["source"], "commit", "-m", "failing release")
    git(rollout["source"], "push", "origin", "qa")
    result = invoke(rollout, DOCKER_FAIL_ON="pull --ignore-buildable")
    assert result.returncode != 0
    assert git(rollout["device"], "rev-parse", "HEAD") == previous
    assert local.read_bytes() == expected


def test_genuine_tracked_modification_aborts_before_fetch(rollout):
    (rollout["device"] / "docker-compose.yaml").write_text("locally changed\n")
    result = invoke(rollout)
    assert result.returncode != 0
    assert "Tracked local changes found; rollout aborted" in result.stderr
    assert not rollout["calls"].exists()


def test_migration_runs_in_existing_api_and_never_deletes_volumes(rollout):
    assert invoke(rollout).returncode == 0
    calls = rollout["calls"].read_text()
    assert "exec -T api python -m entrypoints.migrate" in calls
    assert " compose run " not in calls
    forbidden = ("down --volumes", "volume prune", "docker volume", "-v")
    assert not any(item in calls for item in forbidden)


def test_matching_commit_is_noop(rollout):
    assert invoke(rollout).returncode == 0
    rollout["calls"].write_text("")
    result = invoke(rollout)
    assert result.returncode == 0 and "No update:" in result.stdout
    assert rollout["calls"].read_text() == ""


def test_channels_restricted_before_git_or_docker(rollout):
    text = rollout["config"].read_text().replace('DEPLOY_BRANCH="qa"', 'DEPLOY_BRANCH="dev"')
    rollout["config"].write_text(text)
    result = invoke(rollout)
    assert result.returncode != 0 and "allowed: qa, main" in result.stderr
    assert not rollout["calls"].exists()


def test_existing_config_values_are_preserved_by_installer():
    setup = SETUP.read_text()
    assert "if [[ ! -e $CONFIG_FILE || $REPLACE_CONFIG == true ]]" in setup
    assert 'else log "Preserving $CONFIG_FILE";fi' in setup
    assert "--replace-config" in setup


def test_success_atomically_refreshes_installed_runtime(rollout):
    old_runtime = rollout["runtime"].read_bytes()
    result = invoke(rollout)
    assert result.returncode == 0, result.stderr + result.stdout
    assert rollout["runtime"].read_bytes() != old_runtime
    assert rollout["runtime"].read_bytes() == (rollout["device"] / "piTerminal/rollout/disti-update").read_bytes()
    assert "refreshed for the next run" in result.stdout


def test_updater_retains_lock_fetch_validation_pull_wait_and_rollback_guards():
    update = UPDATER.read_text()
    for expected in ("flock -n", "git fetch --prune origin", "config --quiet",
                     "pull --ignore-buildable", "--remove-orphans --wait --wait-timeout",
                     "CRITICAL: rollback failed", "qa|main"):
        assert expected in update
    assert "git clean" not in update
    assert "docker-compose.raspberry.yaml" not in update
