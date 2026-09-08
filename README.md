# DISTI

DISTI uses a Raspberry Pi controller, TimescaleDB, Flask, Grafana,
Mosquitto and nginx. Local I2C acquisition is deliberately isolated in the
`hardware-agent`; MQTT remains available for external modules and integrations,
but is not in the local acquisition path.

## First-time setup

```sh
cp disti.env.example disti.env
nano disti.env                       # replace every change-me value
docker compose up -d postgres
docker compose run --rm backend python migrate.py
docker compose up -d
```

`disti.env` is the single device-local application configuration file. It is
ignored by Git and is never replaced by provisioning or rollout. The tracked
`disti.env.example` is the canonical safe template. In particular,
`DOCKER_MQTT_INIT_USERNAME` and `DOCKER_MQTT_INIT_PASSWORD` are the only MQTT
credentials an operator maintains.

At every broker start, the DISTI Mosquitto entrypoint validates those variables
and uses `mosquitto_passwd` to create a mode-0600 hashed password file under
`/run/mosquitto` inside the container. The plaintext password is neither logged
nor stored in a second host file. Mosquitto continues to run with anonymous
access disabled and `password_file` authentication enabled.

nginx does not contain an `auth_basic` directive and does not read an
`.htpasswd`; its former mount was unused and has been removed. Browser login is
handled by Grafana at the `/` route. If HTTP Basic authentication is introduced
later, its credential provisioning must be designed explicitly rather than
committing an `.htpasswd`.

## Hardware modes

* **mock** (default): set `DISTI_HARDWARE_MODE=mock`. Deterministic elapsed-time
  temperature and EC curves are written every `DISTI_POLL_INTERVAL_SECONDS`.
  No devices or privileged containers are needed.
* **replay**: set `DISTI_HARDWARE_MODE=replay` and `DISTI_REPLAY_RUN_ID` to a
  recorded run UUID. `DISTI_REPLAY_SPEED=10` runs ten times faster; set
  `DISTI_REPLAY_PRESERVE_TIMING=false` to emit as quickly as possible.
* **raspberry**: currently an intentional provider stub. Once drivers exist,
  start with the `docker-compose.raspberry.yaml` overlay. Only hardware-agent
  receives `/dev/i2c-1`; the rest of the stack is not privileged.

The agent's health endpoint is `http://controller:8081`; backend health is
`/health`. Raw ADC counts and millivolts are always persisted alongside
uncorrected/calibrated values and calibration identity.

Seed a complete fixed 91-minute engineering run with:

```sh
docker compose run --rm backend python seed_mock_run.py
```

The seed is idempotent and includes BoilerTop, raw and placeholder-calibrated
EC, sensor temperature, stable and late-run phases, three fractions, a manual
HEART cut, and fraction-collector events.

## Release and update channels

The immutable promotion path is `dev -> qa -> main`: `dev` is development-only,
the hardware validation controller automatically tracks `qa`, and delivered
devices automatically track `main`. The installed updater independently rejects
`dev`. The legacy `development` branch is not an update channel and is untouched.

`scripts/update-status.sh` fetches and compares the device-local configured
remote commit. `scripts/safe-update.sh` delegates to the VENTI-parity runtime
updater, which refuses tracked changes, deploys the exact remote commit,
validates and restarts Compose, applies additive migrations, waits for
`/healthz`, and fully revalidates the previous application revision after a
failure. Database migrations are forward-compatible and are not destructively
rolled back.

## API and engineering data

The Flask API supports sensor discovery and calibration history/activation,
run start/stop, fraction boundaries and manual cuts. The
`measurement_derivatives` view provides d/dt and d²/dt² for temperature and EC;
`distillation_timeline` combines readings, fractions, cuts, and actuator events
for direct Grafana queries.

## Reference implementation note

The VENTI technical handoff is the rollout and provisioning reference. DISTI
preserves its TimescaleDB, hardware-agent, Grafana, and local-I2C architecture;
it intentionally does not port ChirpStack, InfluxDB, Panstamp, or local-hardware
MQTT coupling.

## Remaining physical hardware work

Implement and bench-test concrete `ADCReader`, `TemperatureProvider`, and
`FractionCollector` adapters for ADS1115, DS2482-100/PT1000 and the selected I2C
stepper controller. Confirm gain/reference voltage, EC compensation/model,
1-Wire topology, I2C addresses, HOME interlocks, position limits, recovery after
brownouts, and Raspberry group/device permissions before enabling raspberry
mode. Mock and replay modes intentionally make none of these assumptions.

## Raspberry client provisioning

Provisioning follows the VENTI client pattern while retaining DISTI's Compose
and hardware architecture. Automatic clients accept only `qa` and `main`; the
default is `main`. The `dev` branch is never accepted by the installed updater.

Before provisioning, place the client WireGuard file at the ignored path
`piTerminal/client-configs/wg0.conf`. For the owner's QA controller run:

```sh
sudo ./piTerminal/setup_client.sh --rollout-branch qa
```

For a delivered production controller run:

```sh
sudo ./piTerminal/setup_client.sh
```

Both commands default to the Raspberry Compose profile, which applies
`docker-compose.yaml` plus `docker-compose.raspberry.yaml`. Use
`--rollout-compose-profile base` only for a device without local I2C access.
Docker, WireGuard, graphical kiosk, and rollout are installed by default;
`--skip-docker`, `--skip-wireguard`, `--no-kiosk`, and `--no-rollout` support
pre-provisioned or headless clients. Huawei-compatible USB modem recovery is
opt-in through `--usb-modem-recovery`.

The rollout installer copies the runtime updater outside the checkout to
`/usr/local/sbin/disti-update`, creates the preserved device-local
`/etc/disti-update.conf`, and enables a persistent, randomized systemd timer.
The installer creates `disti.env` from the safe example only when it is absent
and otherwise preserves it. New `/etc/disti-update.conf` files point directly
to that file. `.disti-local/` is retained in `.gitignore` only so data left by
older installations cannot be committed; the current rollout owns no files
there. Existing `/etc/disti-update.conf` files are preserved unless
`--replace-config` is requested.

On a controller upgraded from the older layout, copy the active values from
`.disti-local/disti.env` to the repository-root `disti.env`, then rerun
`setup_rollout.sh --replace-config` with the controller's existing branch and
profile selections. After successful startup, remove the obsolete local MQTT
password and nginx htpasswd copies. Updates reset only tracked files, so the
root `disti.env` and any ignored migration leftovers are not overwritten.

Useful diagnostics:

```sh
sudo -u pi /usr/local/sbin/disti-update
systemctl list-timers disti-update.timer
journalctl -u disti-update.service --since today
curl http://127.0.0.1:5000/healthz
curl http://127.0.0.1:5000/watchdog/status
```

The kiosk is installed in the user's graphical session using labwc, LXDE, or
XDG autostart. `/etc/disti-kiosk.conf` is created once and remains local. Its
launcher waits for nginx, uses a nonblocking per-session lock, and starts either
`chromium` or `chromium-browser`; an outer loop retries ten seconds after exit.
The default URL is the operational nginx/Grafana entry point; nginx and the
kiosk both use the Grafana route at `/`.

## Watchdog security and behavior

`disti-watchdog` monitors Flask liveness, aggregate PostgreSQL/hardware-agent
status, and measurement freshness. Before a targeted restart it rechecks
transient backend failures and records container state and recent logs. Restarts
are bounded by per-service cooldown and a shared hourly budget. The watchdog
requires `/var/run/docker.sock`; this grants host-level Docker control and is an
explicit deployment tradeoff inherited from VENTI.
