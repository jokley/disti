# DISTI

DISTI uses a Raspberry Pi controller, TimescaleDB, Flask, Grafana,
Mosquitto and nginx. Local I2C acquisition is deliberately isolated in the
`hardware-agent`; MQTT remains available for external modules and integrations,
but is not in the local acquisition path.

## First-time setup

```sh
cp disti.env.example disti.env
nano disti.env                            # replace every change-me value
docker compose up -d --build postgres backend
docker compose exec -T backend python migrate.py
docker compose up -d
```

Migrations run inside the already allocated backend container. Do not use
`docker compose run` for migrations: this stack assigns static service IPs, so
an extra one-off backend container can collide with the running backend's IP.
The `--build` is also required because migrations are copied into the backend
image rather than bind-mounted from the checkout. Without it, `exec` can run an
older copy of `migrate.py` and its SQL even when the Git working tree is current.

After pulling a migration fix on an already-running QA controller, refresh the
backend image and container before retrying it:

```sh
docker compose build backend
docker compose up -d --no-deps --force-recreate backend
docker compose exec -T backend python migrate.py
docker compose up -d
```

On the ARM64 Pi, rebuild and recreate both Python runtime services with the
Raspberry hardware overlay (without restarting their dependencies):

```sh
docker compose -f docker-compose.yaml -f docker-compose.raspberry.yaml up -d --build --no-deps --force-recreate backend hardware-agent
```

Migrations run inside the already allocated backend container. Do not use
`docker compose run` for migrations: this stack assigns static service IPs, so
an extra one-off backend container can collide with the running backend's IP.

`disti.env` is the single device-local application configuration file. It is
ignored by Git and is never replaced by provisioning or rollout. Repository-root
`.env` is neither read nor required for normal DISTI operation. The tracked
`disti.env.example` is the canonical safe template. In particular,
`MQTT_USERNAME` and `MQTT_PASSWORD` are the only MQTT
credentials an operator maintains.

Grafana receives its native `GF_SECURITY_ADMIN_USER` and
`GF_SECURITY_ADMIN_PASSWORD` variables directly. Grafana datasource provisioning reads the same
PostgreSQL variables directly. Mosquitto receives the MQTT variables unchanged
and generates its hashed runtime-only password file before broker startup. Any
MQTT client, including the provided Telegraf configuration, uses those same two
variable names.

The same file supplies PostgreSQL initialization and every database client,
using one canonical contract: `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`,
and `POSTGRES_PASSWORD`. Compose injects `disti.env` directly into PostgreSQL,
backend, hardware-agent, watchdog, and Grafana, so normal operator commands do
not need `--env-file`:

```sh
docker compose up -d --build
docker compose down
docker compose ps
docker compose logs
```

Controllers configured with legacy credential names require a one-time edit of
`disti.env`: retain each existing value while renaming the PostgreSQL, Grafana,
and MQTT keys to the canonical names shown in `disti.env.example`. Then rebuild
and recreate the containers without removing the named database volume:

```sh
docker compose up -d --build --force-recreate
docker compose exec -T backend python migrate.py
docker compose ps
```

PostgreSQL applies initialization variables only when its data directory is
first initialized. Renaming these environment keys while preserving their
values does not reinitialize PostgreSQL and does not require deleting the
volume. Never add `--volumes` to `docker compose down` for this procedure and
do not remove `disti_db_data`.

At every broker start, the DISTI Mosquitto entrypoint validates those variables
and uses `mosquitto_passwd` to create a mode-0600 hashed password file in a
unique temporary path under `/run/mosquitto`. It resolves the image's
`mosquitto` UID/GID at runtime, gives that user access, and atomically replaces
the configured file before handing off to the upstream entrypoint. Thus a
restart safely replaces the previous generated file and a container recreation
starts cleanly; no generated credential state is persisted. The plaintext
password is neither logged nor stored in a second host file. Mosquitto continues
to run with anonymous access disabled and `password_file` authentication
enabled.

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
* **raspberry**: set `DISTI_HARDWARE_MODE=raspberry` to use the ADS1115 adapter,
  then start with the `docker-compose.raspberry.yaml` overlay. Only
  hardware-agent receives `/dev/i2c-1`; the rest of the stack is not privileged.

### ADS1115 Raspberry configuration and validation

The first two single-ended inputs are configured as follows: ADS1115 A0 is
`ec-1` (`ec`) from the DFRobot EC conversion board, and A1 is `ec-temp`
(`temperature`) from its separate PT1000 conversion board. A2 and A3 remain
electrically available but unassigned. DISTI stores the signed ADC count and
uncalibrated millivolts for both inputs. Because no validated EC or PT1000
formula exists yet, `value` is also the raw millivolt signal with unit `mV`,
and metadata explicitly says that engineering conversion is not configured.
Calibration and temperature compensation must remain downstream.

The device-local settings are:

```dotenv
DISTI_ADC_TYPE=ads1115
DISTI_I2C_BUS=1
DISTI_ADS1115_ADDRESS=0x48
DISTI_ADS1115_EC_CHANNEL=0
DISTI_ADS1115_PT1000_CHANNEL=1
DISTI_ADS1115_GAIN=1
DISTI_ADS1115_DATA_RATE=128
```

Gain 1 (±4.096 V full scale) and 128 samples/second are conservative initial
defaults, not final electrical design choices. Confirm that the conversion
boards' full output range cannot exceed the selected PGA range, and confirm
noise/settling at the installed sample rate, before physical sign-off. The
configured address is authoritative; `0x48` is merely the expected address
when ADS1115 ADDR is tied to ground. Use a common ground and appropriate I2C
level adaptation; connect EC analog output to A0 and PT1000-board analog output
to A1. Never apply an analog input outside ADS1115 supply/absolute limits.

On the Pi, enable I2C and validate the host before starting DISTI:

```sh
ls -l /dev/i2c-*
sudo apt-get install -y i2c-tools              # if i2cdetect is absent
i2cdetect -y 1                                 # expect 48 unless configured otherwise
nano disti.env                                 # change mock to raspberry; confirm ADC settings
docker compose -f docker-compose.yaml -f docker-compose.raspberry.yaml up -d --build
curl http://127.0.0.1:8081/healthz
docker compose logs --tail=100 hardware-agent
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT time,sensor_id,measurement_type,raw_value,raw_mv,value,unit,quality,metadata FROM sensor_measurements WHERE sensor_id IN ('ec-1','ec-temp') ORDER BY time DESC LIMIT 10;"
```

Run the `psql` command from a shell where the device-local values have been
exported, or substitute its configured database/user values. Healthy Raspberry
status reports I2C availability, ADS1115 reachability, acquisition state, and
the last successful read. A missing bus/device or transient read changes health
to degraded with `last_error`; the process backs off and retries, and the ADC
adapter reopens the bus after a read error rather than requiring a stack restart.
To return to simulation, set `DISTI_HARDWARE_MODE=mock` and start normal base
Compose with `docker compose up -d --build` (without the Raspberry overlay).

The agent's health endpoint is `http://127.0.0.1:8081/healthz` on the host and
`http://hardware-agent:8081/healthz` inside Compose; backend health is
`http://127.0.0.1:5000/healthz`. Raw ADC counts and millivolts are always
persisted alongside uncorrected/calibrated values and calibration identity.

Seed a complete fixed 91-minute engineering run with:

```sh
docker compose exec -T backend python seed_mock_run.py
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
calibration API retains its `offset` field for client compatibility and maps it
to the database's non-reserved `calibration_offset` column. The
`measurement_derivatives` view provides d/dt and d²/dt² for temperature and EC;
`distillation_timeline` combines readings, fractions, cuts, and actuator events
for direct Grafana queries.

## Reference implementation note

The VENTI technical handoff is the rollout and provisioning reference. DISTI
preserves its TimescaleDB, hardware-agent, Grafana, and local-I2C architecture;
it intentionally does not port ChirpStack, InfluxDB, Panstamp, or local-hardware
MQTT coupling.

## Remaining physical hardware work

Bench-test the ADS1115 adapter and implement concrete `TemperatureProvider` and
`FractionCollector` adapters for later hardware. Confirm gain/reference voltage, EC compensation/model,
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
and otherwise preserves it. The updater requires that repository-root file.
`.disti-local/` is retained in `.gitignore` only so data left by older
installations cannot be committed; the current rollout owns no files there.
Existing `/etc/disti-update.conf` files are preserved unless `--replace-config`
is requested.

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
